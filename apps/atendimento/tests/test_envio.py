"""Envio de itens: preço calculado no servidor, validação e idempotência."""
from decimal import Decimal

from django.test import override_settings

from apps.atendimento import servicos
from apps.atendimento.excecoes import DadosInvalidos
from apps.atendimento.models import Envio, ItemComanda

from .base import CenarioBase

REF_A = '10000000-0000-4000-8000-000000000001'
REF_B = '10000000-0000-4000-8000-000000000002'


class PrecoCalculadoNoServidor(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

    def test_preco_enviado_pelo_navegador_e_ignorado(self):
        """O cenário clássico de adulteração: o cliente manda preço 0,01."""
        item = self.item(self.xsalada, quantidade=2)
        item['preco'] = '0.01'
        item['valor'] = '0.01'
        item['subtotal'] = '0.02'
        item['total'] = '0.02'

        servicos.enviar_itens(self.comanda.pk, REF_A, [item], self.garcom)

        gravado = ItemComanda.objects.get(comanda=self.comanda)
        self.assertEqual(gravado.preco_unitario, Decimal('26.00'))
        self.assertEqual(gravado.subtotal, Decimal('52.00'))
        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.total(), Decimal('52.00'))

    def test_adicionais_entram_no_preco_com_o_valor_do_catalogo(self):
        servicos.enviar_itens(
            self.comanda.pk, REF_A,
            [self.item(self.xsalada, quantidade=2, adicionais=[self.bacon_extra])],
            self.garcom,
        )

        item = ItemComanda.objects.get(comanda=self.comanda)
        self.assertEqual(item.preco_unitario, Decimal('26.00'))
        self.assertEqual(item.preco_adicionais, Decimal('6.00'))
        self.assertEqual(item.subtotal, Decimal('64.00'))  # (26 + 6) x 2
        self.assertEqual(item.adicionais_detalhe[0]['nome'], 'Bacon extra')

    def test_meio_a_meio_cobra_o_sabor_mais_caro(self):
        servicos.enviar_itens(
            self.comanda.pk, REF_A,
            [self.item(self.pizza_barata, segundo_sabor=self.pizza_cara)],
            self.garcom,
        )

        item = ItemComanda.objects.get(comanda=self.comanda)
        self.assertEqual(item.preco_unitario, Decimal('62.00'))
        self.assertIn('Meio a meio', item.descricao)

    @override_settings(ATENDIMENTO_REGRA_MEIO_A_MEIO='media')
    def test_regra_de_meio_a_meio_e_configuravel(self):
        servicos.enviar_itens(
            self.comanda.pk, REF_A,
            [self.item(self.pizza_barata, segundo_sabor=self.pizza_cara)],
            self.garcom,
        )

        item = ItemComanda.objects.get(comanda=self.comanda)
        self.assertEqual(item.preco_unitario, Decimal('58.50'))  # (55 + 62) / 2

    def test_preco_do_catalogo_alterado_depois_nao_muda_conta_ja_lancada(self):
        servicos.enviar_itens(self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom)

        self.xsalada.preco = Decimal('99.00')
        self.xsalada.save()

        self.comanda.refresh_from_db()
        item = ItemComanda.objects.get(comanda=self.comanda)
        self.assertEqual(item.preco_unitario, Decimal('26.00'))
        self.assertEqual(self.comanda.total(), Decimal('26.00'))


class ValidacaoDeItens(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

    def _recusa(self, itens):
        with self.assertRaises(DadosInvalidos):
            servicos.enviar_itens(self.comanda.pk, REF_A, itens, self.garcom)
        self.assertEqual(ItemComanda.objects.filter(comanda=self.comanda).count(), 0)
        self.assertEqual(Envio.objects.filter(comanda=self.comanda).count(), 0)

    def test_quantidade_zero(self):
        self._recusa([self.item(self.xsalada, quantidade=0)])

    def test_quantidade_negativa(self):
        self._recusa([self.item(self.xsalada, quantidade=-3)])

    def test_quantidade_fracionada(self):
        self._recusa([self.item(self.xsalada, quantidade=1.5)])

    def test_quantidade_acima_do_limite(self):
        self._recusa([self.item(self.xsalada, quantidade=1000)])

    def test_produto_inexistente(self):
        self._recusa([{'produto_id': 999999, 'quantidade': 1, 'adicionais': []}])

    def test_produto_inativo(self):
        self._recusa([self.item(self.produto_inativo)])

    def test_produto_indisponivel(self):
        self._recusa([self.item(self.produto_indisponivel)])

    def test_adicional_indisponivel(self):
        self._recusa([self.item(self.xsalada, adicionais=[self.adicional_indisponivel])])

    def test_adicional_de_outra_categoria(self):
        """Gelo e limão é adicional de bebida; não pode entrar em um lanche."""
        self._recusa([self.item(self.xsalada, adicionais=[self.gelo_limao])])

    def test_meio_a_meio_com_produto_que_nao_permite(self):
        self._recusa([self.item(self.xsalada, segundo_sabor=self.xbacon)])

    def test_meio_a_meio_entre_categorias_diferentes(self):
        self.refrigerante.permite_meio_a_meio = True
        self.refrigerante.save()
        self.pizza_cara.refresh_from_db()
        self._recusa([self.item(self.pizza_cara, segundo_sabor=self.refrigerante)])

    def test_lista_vazia(self):
        self._recusa([])

    def test_um_item_invalido_no_meio_impede_o_lote_inteiro(self):
        """Ou grava tudo, ou não grava nada: nunca meio pedido no banco."""
        itens = [
            self.item(self.xsalada),
            self.item(self.produto_inativo),
            self.item(self.refrigerante),
        ]
        self._recusa(itens)


class Idempotencia(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

    def test_mesmo_envio_repetido_nao_duplica_itens(self):
        primeiro = servicos.enviar_itens(
            self.comanda.pk, REF_A, [self.item(self.xsalada, quantidade=2)], self.garcom
        )
        segundo = servicos.enviar_itens(
            self.comanda.pk, REF_A, [self.item(self.xsalada, quantidade=2)], self.garcom
        )

        self.assertFalse(primeiro['duplicado'])
        self.assertTrue(segundo['duplicado'])
        self.assertEqual(ItemComanda.objects.filter(comanda=self.comanda).count(), 1)
        self.assertEqual(Envio.objects.filter(comanda=self.comanda).count(), 1)

        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.total(), Decimal('52.00'))

    def test_reenvio_devolve_o_mesmo_resultado(self):
        servicos.enviar_itens(self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom)
        repetido = servicos.enviar_itens(
            self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom
        )

        self.assertEqual(repetido['comanda']['total'], '26.00')
        self.assertEqual(repetido['itens_gravados'], 1)

    def test_dois_envios_distintos_sao_ambos_preservados(self):
        servicos.enviar_itens(self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom)
        servicos.enviar_itens(
            self.comanda.pk, REF_B, [self.item(self.refrigerante, quantidade=2)], self.outro_garcom
        )

        self.comanda.refresh_from_db()
        self.assertEqual(ItemComanda.objects.filter(comanda=self.comanda).count(), 2)
        self.assertEqual(self.comanda.total(), Decimal('40.00'))  # 26 + 14

        # Rodada nova não reenvia a rodada anterior como se fosse nova.
        descricoes = list(
            ItemComanda.objects.filter(comanda=self.comanda).values_list('descricao', flat=True)
        )
        self.assertEqual(descricoes, ['X-Salada', 'Refrigerante lata'])

    def test_dois_garcons_diferentes_ficam_registrados_por_item(self):
        servicos.enviar_itens(self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom)
        servicos.enviar_itens(self.comanda.pk, REF_B, [self.item(self.refrigerante)], self.outro_garcom)

        responsaveis = set(
            ItemComanda.objects.filter(comanda=self.comanda).values_list(
                'criado_por__username', flat=True
            )
        )
        self.assertEqual(responsaveis, {self.garcom.username, self.outro_garcom.username})

    def test_referencia_invalida_e_recusada(self):
        with self.assertRaises(DadosInvalidos):
            servicos.enviar_itens(self.comanda.pk, 'nao-e-um-uuid', [self.item(self.xsalada)], self.garcom)

    def test_referencia_de_outra_comanda_e_recusada(self):
        outra, _ = servicos.abrir_ou_recuperar_comanda(6, self.garcom)
        servicos.enviar_itens(outra.pk, REF_A, [self.item(self.xsalada)], self.garcom)

        with self.assertRaises(DadosInvalidos):
            servicos.enviar_itens(self.comanda.pk, REF_A, [self.item(self.xsalada)], self.garcom)
