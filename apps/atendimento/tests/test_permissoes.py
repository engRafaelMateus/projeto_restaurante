"""
Autorização no servidor.

A interface esconde botões; estes testes garantem que esconder o botão não é a
proteção. Toda operação é exercitada pela URL real, com sessão real.
"""
import json

from django.urls import reverse

from apps.atendimento import servicos
from apps.atendimento.models import Comanda, ItemComanda, Pagamento

from .base import CenarioBase

REF = '30000000-0000-4000-8000-000000000001'


class AcessoSemAutenticacao(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

    def test_visitante_nao_grava_pedido(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data=json.dumps({'referencia_envio': REF, 'itens': [self.item(self.xsalada)]}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(ItemComanda.objects.count(), 0)

    def test_visitante_nao_abre_comanda(self):
        resposta = self.client.post(
            reverse('atendimento:api_abrir_comanda'),
            data=json.dumps({'mesa': 6}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(Comanda.objects.count(), 1)

    def test_visitante_nao_lista_o_catalogo(self):
        """Preços e produtos não são públicos: o cardápio do salão exige sessão."""
        resposta = self.client.get(reverse('atendimento:api_catalogo'))
        self.assertEqual(resposta.status_code, 401)

    def test_visitante_nao_ve_o_estado_do_salao(self):
        resposta = self.client.get(reverse('atendimento:api_estado'))
        self.assertEqual(resposta.status_code, 401)

    def test_tela_do_caixa_redireciona_para_login(self):
        resposta = self.client.get(reverse('atendimento:caixa'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/entrar/', resposta['Location'])


class LimitesDoGarcom(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(self.comanda.pk, REF, [self.item(self.xsalada)], self.garcom)
        self.autenticar(self.garcom)

    def test_garcom_pode_lancar_itens(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data=json.dumps(
                {
                    'referencia_envio': '30000000-0000-4000-8000-000000000009',
                    'itens': [self.item(self.refrigerante)],
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['ok'])

    def test_garcom_nao_registra_pagamento(self):
        resposta = self.client.post(
            reverse('atendimento:api_registrar_pagamento', args=[self.comanda.pk]),
            data=json.dumps({'meio': 'pix'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Pagamento.objects.exists())
        self.comanda.refresh_from_db()
        self.assertTrue(self.comanda.esta_aberta)

    def test_garcom_nao_cancela_item_enviado(self):
        item = self.comanda.itens.first()

        resposta = self.client.post(
            reverse('atendimento:api_cancelar_item', args=[item.pk]),
            data=json.dumps({'motivo': 'quero cancelar'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 403)
        item.refresh_from_db()
        self.assertFalse(item.cancelado)

    def test_garcom_nao_ve_historico_financeiro(self):
        """Autenticado sem permissão recebe 403, não um laço de redirecionamento."""
        resposta = self.client.get(reverse('atendimento:historico'))
        self.assertEqual(resposta.status_code, 403)

    def test_garcom_consulta_comandas_abertas(self):
        resposta = self.client.get(reverse('atendimento:api_estado'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['ok'])


class PoderesDoCaixa(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        servicos.enviar_itens(self.comanda.pk, REF, [self.item(self.xsalada)], self.garcom)
        self.autenticar(self.caixa)

    def test_caixa_registra_pagamento(self):
        resposta = self.client.post(
            reverse('atendimento:api_registrar_pagamento', args=[self.comanda.pk]),
            data=json.dumps({'meio': 'credito'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(Pagamento.objects.filter(comanda=self.comanda).exists())

    def test_caixa_cancela_item_com_motivo(self):
        item = self.comanda.itens.first()

        resposta = self.client.post(
            reverse('atendimento:api_cancelar_item', args=[item.pk]),
            data=json.dumps({'motivo': 'item veio errado'}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.cancelado)

    def test_caixa_ve_o_historico(self):
        resposta = self.client.get(reverse('atendimento:historico'))
        self.assertEqual(resposta.status_code, 200)

    def test_pagamento_repetido_pela_api_nao_duplica_cobranca(self):
        url = reverse('atendimento:api_registrar_pagamento', args=[self.comanda.pk])
        corpo = json.dumps({'meio': 'pix'})

        primeira = self.client.post(url, data=corpo, content_type='application/json')
        segunda = self.client.post(url, data=corpo, content_type='application/json')

        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 409)
        self.assertEqual(Pagamento.objects.filter(comanda=self.comanda).count(), 1)


class EntradasMalformadas(CenarioBase):
    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)
        self.autenticar(self.garcom)

    def test_corpo_que_nao_e_json(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data='isto não é json',
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json()['codigo'], 'json_invalido')

    def test_json_que_nao_e_objeto(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data='[1, 2, 3]',
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 400)

    def test_metodo_get_em_endpoint_de_escrita(self):
        resposta = self.client.get(reverse('atendimento:api_abrir_comanda'))
        self.assertEqual(resposta.status_code, 405)

    def test_comanda_inexistente(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[999999]),
            data=json.dumps(
                {'referencia_envio': REF, 'itens': [self.item(self.xsalada)]}
            ),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 404)

    def test_resposta_de_erro_nao_vaza_detalhe_interno(self):
        resposta = self.client.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data=json.dumps({'referencia_envio': REF, 'itens': [self.item(self.produto_inativo)]}),
            content_type='application/json',
        )

        conteudo = resposta.content.decode()
        self.assertEqual(resposta.status_code, 400)
        self.assertNotIn('Traceback', conteudo)
        self.assertNotIn('SELECT', conteudo.upper())


class ProtecaoCsrf(CenarioBase):
    """Toda mutação passa pelo CSRF do Django. Nenhum endpoint é isento."""

    def setUp(self):
        self.comanda, _ = servicos.abrir_ou_recuperar_comanda(5, self.garcom)

    def test_post_sem_token_csrf_e_recusado(self):
        cliente = self.client_class(enforce_csrf_checks=True)
        cliente.login(username=self.garcom.username, password='senha-de-teste-123')

        resposta = cliente.post(
            reverse('atendimento:api_enviar_itens', args=[self.comanda.pk]),
            data=json.dumps({'referencia_envio': REF, 'itens': [self.item(self.xsalada)]}),
            content_type='application/json',
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(ItemComanda.objects.count(), 0)
