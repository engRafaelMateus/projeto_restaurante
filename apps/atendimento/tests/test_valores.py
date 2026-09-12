"""Aritmética de dinheiro e atomicidade das operações."""
from decimal import Decimal
from unittest import mock

from apps.atendimento import servicos
from apps.atendimento.models import Envio, ItemComanda
from apps.atendimento.valores import dinheiro, formatar_brl, somar
from apps.cardapio.models import Produto

from .base import CenarioBase

REF = '40000000-0000-4000-8000-000000000001'


class Arredondamento(CenarioBase):
    def test_metade_para_cima(self):
        self.assertEqual(dinheiro('1.005'), Decimal('1.01'))
        self.assertEqual(dinheiro('2.675'), Decimal('2.68'))
        self.assertEqual(dinheiro('0.004'), Decimal('0.00'))

    def test_nao_usa_ponto_flutuante(self):
        """A soma que quebra em float: 0.1 + 0.2 == 0.30000000000000004."""
        self.assertEqual(somar(['0.1', '0.2']), Decimal('0.30'))

    def test_formatacao_brasileira(self):
        self.assertEqual(formatar_brl(Decimal('1234.5')), 'R$ 1.234,50')
        self.assertEqual(formatar_brl(Decimal('0')), 'R$ 0,00')
        self.assertEqual(formatar_brl(Decimal('1234567.89')), 'R$ 1.234.567,89')

    def test_total_independe_da_ordem_dos_itens(self):
        """Arredondar por linha e depois somar torna o total estável."""
        barato = Produto.objects.create(
            categoria=self.lanches, nome='Item A', preco=Decimal('3.33')
        )
        caro = Produto.objects.create(
            categoria=self.lanches, nome='Item B', preco=Decimal('7.77')
        )

        comanda_um, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(
            comanda_um.pk, REF,
            [self.item(barato, quantidade=3), self.item(caro, quantidade=3)],
            self.garcom,
        )

        comanda_dois, _ = servicos.abrir_ou_recuperar_comanda(6, self.garcom)
        servicos.enviar_itens(
            comanda_dois.pk, '40000000-0000-4000-8000-000000000002',
            [self.item(caro, quantidade=3), self.item(barato, quantidade=3)],
            self.garcom,
        )

        self.assertEqual(comanda_um.total(), comanda_dois.total())
        self.assertEqual(comanda_um.total(), Decimal('33.30'))  # 9,99 + 23,31

    def test_totais_do_modelo_sao_decimal(self):
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(comanda.pk, REF, [self.item(self.xsalada)], self.garcom)

        self.assertIsInstance(comanda.total(), Decimal)


class AtomicidadeDoEnvio(CenarioBase):
    def test_falha_no_meio_da_gravacao_nao_deixa_registro_parcial(self):
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

        with mock.patch.object(
            ItemComanda.objects, 'bulk_create', side_effect=RuntimeError('falha simulada no banco')
        ):
            with self.assertRaises(RuntimeError):
                servicos.enviar_itens(
                    comanda.pk, REF,
                    [self.item(self.xsalada), self.item(self.refrigerante)],
                    self.garcom,
                )

        # Nem o envio nem os itens sobreviveram: a transação foi desfeita.
        self.assertEqual(Envio.objects.filter(comanda=comanda).count(), 0)
        self.assertEqual(ItemComanda.objects.filter(comanda=comanda).count(), 0)
        comanda.refresh_from_db()
        self.assertEqual(comanda.total(), Decimal('0.00'))

    def test_envio_pode_ser_refeito_depois_da_falha(self):
        """Depois de uma falha, a mesma referência ainda está livre."""
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

        with mock.patch.object(
            ItemComanda.objects, 'bulk_create', side_effect=RuntimeError('falha simulada')
        ):
            with self.assertRaises(RuntimeError):
                servicos.enviar_itens(comanda.pk, REF, [self.item(self.xsalada)], self.garcom)

        resultado = servicos.enviar_itens(comanda.pk, REF, [self.item(self.xsalada)], self.garcom)

        self.assertFalse(resultado['duplicado'])
        self.assertEqual(ItemComanda.objects.filter(comanda=comanda).count(), 1)
