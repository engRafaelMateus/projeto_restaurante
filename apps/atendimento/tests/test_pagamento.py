"""Pagamento manual, troco, encerramento e cancelamento de item."""
from decimal import Decimal

from apps.atendimento import servicos
from apps.atendimento.excecoes import ConflitoDeEstado, DadosInvalidos
from apps.atendimento.models import Comanda, Pagamento

from .base import CenarioBase

REF = '20000000-0000-4000-8000-000000000001'
REF2 = '20000000-0000-4000-8000-000000000002'


class RegistroDePagamento(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(
            self.comanda.pk, REF,
            [self.item(self.xsalada, quantidade=2), self.item(self.refrigerante)],
            self.garcom,
        )
        self.total_esperado = Decimal('59.00')  # 26x2 + 7

    def test_pagamento_em_dinheiro_calcula_troco(self):
        pagamento = servicos.registrar_pagamento(
            self.comanda.pk, {'meio': 'dinheiro', 'valor_recebido': '100.00'}, self.caixa
        )

        self.assertEqual(pagamento.valor, self.total_esperado)
        self.assertEqual(pagamento.valor_recebido, Decimal('100.00'))
        self.assertEqual(pagamento.troco, Decimal('41.00'))
        self.assertEqual(pagamento.registrado_por, self.caixa)

    def test_pagamento_em_pix_nao_registra_troco(self):
        pagamento = servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

        self.assertIsNone(pagamento.valor_recebido)
        self.assertIsNone(pagamento.troco)
        self.assertFalse(pagamento.confirma_transacao_externa)

    def test_valor_cobrado_e_recalculado_pelo_servidor(self):
        """Mesmo que o navegador mande um total, ele não é considerado."""
        pagamento = servicos.registrar_pagamento(
            self.comanda.pk,
            {'meio': 'pix', 'valor': '1.00', 'total': '1.00', 'valor_recebido': '1.00'},
            self.caixa,
        )

        self.assertEqual(pagamento.valor, self.total_esperado)

    def test_dinheiro_sem_valor_recebido_e_recusado(self):
        with self.assertRaises(DadosInvalidos):
            servicos.registrar_pagamento(self.comanda.pk, {'meio': 'dinheiro'}, self.caixa)
        self.assertFalse(Pagamento.objects.exists())

    def test_dinheiro_com_valor_menor_que_a_conta_e_recusado(self):
        with self.assertRaises(DadosInvalidos):
            servicos.registrar_pagamento(
                self.comanda.pk, {'meio': 'dinheiro', 'valor_recebido': '10.00'}, self.caixa
            )
        self.assertFalse(Pagamento.objects.exists())

    def test_meio_invalido_e_recusado(self):
        with self.assertRaises(DadosInvalidos):
            servicos.registrar_pagamento(self.comanda.pk, {'meio': 'bitcoin'}, self.caixa)

    def test_pagamento_encerra_a_comanda_e_libera_a_mesa(self):
        servicos.registrar_pagamento(self.comanda.pk, {'meio': 'debito'}, self.caixa)

        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.status, Comanda.Status.PAGA)
        self.assertIsNotNone(self.comanda.encerrada_em)
        self.assertEqual(self.comanda.encerrada_por, self.caixa)
        self.assertFalse(self.mesa5.ocupada)

    def test_pagamento_repetido_e_recusado(self):
        servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

        with self.assertRaises(ConflitoDeEstado):
            servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

        self.assertEqual(Pagamento.objects.filter(comanda=self.comanda).count(), 1)

    def test_comanda_sem_consumo_nao_pode_ser_paga(self):
        vazia, _ = servicos.abrir_ou_recuperar_comanda(6, self.garcom)

        with self.assertRaises(ConflitoDeEstado):
            servicos.registrar_pagamento(vazia.pk, {'meio': 'pix'}, self.caixa)

    def test_historico_preserva_itens_precos_e_responsaveis(self):
        servicos.registrar_pagamento(
            self.comanda.pk, {'meio': 'dinheiro', 'valor_recebido': '60.00'}, self.caixa
        )
        self.xsalada.preco = Decimal('99.00')
        self.xsalada.save()

        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.itens.count(), 2)
        self.assertEqual(self.comanda.total(), self.total_esperado)
        self.assertEqual(self.comanda.pagamento.valor, self.total_esperado)
        self.assertEqual(self.comanda.pagamento.troco, Decimal('1.00'))
        self.assertEqual(
            self.comanda.itens.first().criado_por.username, self.garcom.username
        )


class CancelamentoDeItem(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(
            self.comanda.pk, REF,
            [self.item(self.xsalada, quantidade=2), self.item(self.refrigerante)],
            self.garcom,
        )
        self.item_lanche = self.comanda.itens.first()

    def test_cancelamento_registra_motivo_responsavel_e_horario(self):
        cancelado = servicos.cancelar_item(
            self.item_lanche.pk, 'cliente desistiu do lanche', self.caixa
        )

        self.assertTrue(cancelado.cancelado)
        self.assertEqual(cancelado.cancelado_por, self.caixa)
        self.assertEqual(cancelado.motivo_cancelamento, 'cliente desistiu do lanche')
        self.assertIsNotNone(cancelado.cancelado_em)

    def test_cancelamento_corrige_o_total_sem_apagar_o_item(self):
        servicos.cancelar_item(self.item_lanche.pk, 'saiu errado da cozinha', self.caixa)

        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.total(), Decimal('7.00'))
        self.assertEqual(self.comanda.itens.count(), 2)          # histórico preservado
        self.assertEqual(self.comanda.itens_ativos.count(), 1)

    def test_motivo_vazio_e_recusado(self):
        with self.assertRaises(DadosInvalidos):
            servicos.cancelar_item(self.item_lanche.pk, '  ', self.caixa)

        self.item_lanche.refresh_from_db()
        self.assertFalse(self.item_lanche.cancelado)

    def test_item_ja_cancelado_nao_cancela_de_novo(self):
        servicos.cancelar_item(self.item_lanche.pk, 'primeiro cancelamento', self.caixa)

        with self.assertRaises(ConflitoDeEstado):
            servicos.cancelar_item(self.item_lanche.pk, 'segundo cancelamento', self.caixa)

    def test_nao_cancela_item_de_comanda_encerrada(self):
        servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

        with self.assertRaises(ConflitoDeEstado):
            servicos.cancelar_item(self.item_lanche.pk, 'tarde demais', self.caixa)

    def test_cancelar_todos_os_itens_impede_pagamento_e_permite_cancelar_a_comanda(self):
        for item in self.comanda.itens.all():
            servicos.cancelar_item(item.pk, 'pedido cancelado inteiro', self.caixa)

        with self.assertRaises(ConflitoDeEstado):
            servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

        cancelada = servicos.cancelar_comanda_vazia(
            self.comanda.pk, 'todos os itens cancelados', self.caixa
        )
        self.assertEqual(cancelada.status, Comanda.Status.CANCELADA)
