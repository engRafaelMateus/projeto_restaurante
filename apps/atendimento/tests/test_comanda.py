"""Abertura de comanda, unicidade por mesa e ciclo de vida."""
from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.atendimento import servicos
from apps.atendimento.excecoes import ConflitoDeEstado, NaoEncontrado
from apps.atendimento.models import Comanda

from .base import CenarioBase


class AberturaDeComanda(CenarioBase):
    def test_abrir_mesa_cria_uma_comanda(self):
        comanda, criada = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

        self.assertTrue(criada)
        self.assertEqual(comanda.mesa, self.mesa5)
        self.assertEqual(comanda.status, Comanda.Status.ABERTA)
        self.assertEqual(comanda.aberta_por, self.garcom)

    def test_abrir_a_mesma_mesa_duas_vezes_devolve_a_mesma_comanda(self):
        primeira, criada_primeira = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        segunda, criada_segunda = servicos.abrir_ou_recuperar_comanda(5, self.outro_garcom)

        self.assertEqual(primeira.pk, segunda.pk)
        self.assertTrue(criada_primeira)
        self.assertFalse(criada_segunda)
        self.assertEqual(Comanda.objects.abertas().filter(mesa=self.mesa5).count(), 1)

    def test_banco_recusa_segunda_comanda_aberta_na_mesma_mesa(self):
        """A garantia não está no código da view: está na constraint."""
        Comanda.objects.create(mesa=self.mesa5, aberta_por=self.garcom)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Comanda.objects.create(mesa=self.mesa5, aberta_por=self.outro_garcom)

    def test_mesa_inexistente_e_recusada(self):
        with self.assertRaises(NaoEncontrado):
            servicos.abrir_ou_recuperar_comanda(999, self.garcom)

    def test_mesa_inativa_e_recusada(self):
        self.mesa6.ativa = False
        self.mesa6.save()

        with self.assertRaises(NaoEncontrado):
            servicos.abrir_ou_recuperar_comanda(6, self.garcom)

    def test_mesa_so_fica_ocupada_enquanto_houver_comanda_aberta(self):
        self.assertFalse(self.mesa5.ocupada)

        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        self.assertTrue(self.mesa5.ocupada)

        servicos.enviar_itens(
            comanda.pk, '11111111-1111-4111-8111-111111111111',
            [self.item(self.xsalada)], self.garcom,
        )
        servicos.registrar_pagamento(comanda.pk, {'meio': 'pix'}, self.caixa)

        self.assertFalse(self.mesa5.ocupada)


class ComandaEncerrada(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(
            self.comanda.pk, '22222222-2222-4222-8222-222222222222',
            [self.item(self.xsalada)], self.garcom,
        )
        servicos.registrar_pagamento(self.comanda.pk, {'meio': 'pix'}, self.caixa)

    def test_nao_aceita_novos_itens(self):
        with self.assertRaises(ConflitoDeEstado):
            servicos.enviar_itens(
                self.comanda.pk, '33333333-3333-4333-8333-333333333333',
                [self.item(self.refrigerante)], self.garcom,
            )

    def test_novo_atendimento_gera_outra_comanda_sem_reaproveitar_consumo(self):
        nova, criada = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

        self.assertTrue(criada)
        self.assertNotEqual(nova.pk, self.comanda.pk)
        self.assertEqual(nova.itens.count(), 0)
        self.assertEqual(nova.total(), Decimal('0.00'))

        # O histórico anterior continua intacto.
        self.comanda.refresh_from_db()
        self.assertEqual(self.comanda.status, Comanda.Status.PAGA)
        self.assertEqual(self.comanda.itens.count(), 1)


class CancelamentoDeComandaVazia(CenarioBase):
    def test_comanda_sem_consumo_pode_ser_cancelada_e_libera_a_mesa(self):
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

        cancelada = servicos.cancelar_comanda_vazia(comanda.pk, 'cliente desistiu', self.caixa)

        self.assertEqual(cancelada.status, Comanda.Status.CANCELADA)
        self.assertIsNotNone(cancelada.encerrada_em)
        self.assertEqual(cancelada.encerrada_por, self.caixa)
        self.assertFalse(self.mesa5.ocupada)

    def test_comanda_com_itens_nao_pode_ser_cancelada_como_vazia(self):
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(
            comanda.pk, '44444444-4444-4444-8444-444444444444',
            [self.item(self.xsalada)], self.garcom,
        )

        with self.assertRaises(ConflitoDeEstado):
            servicos.cancelar_comanda_vazia(comanda.pk, 'tentativa indevida', self.caixa)

    def test_comanda_cancelada_nao_conta_como_venda(self):
        comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.cancelar_comanda_vazia(comanda.pk, 'mesa liberada sem consumo', self.caixa)

        comanda.refresh_from_db()
        self.assertFalse(comanda.esta_paga)
        self.assertEqual(comanda.total(), Decimal('0.00'))
