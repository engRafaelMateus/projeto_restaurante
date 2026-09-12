"""
Verificação do fluxo completo em navegador real.

Percorre a jornada de ponta a ponta com **duas sessões independentes**: o
garçom em largura de celular (390px) e o caixa em desktop (1366px), cada um em
seu próprio contexto de navegador — cookies separados, como duas pessoas
diferentes. É o teste que prova que as telas conversam entre si, coisa que
nenhum teste de unidade mostra.

Por que não roda junto com a suíte normal: exige o Chromium do Playwright
(~150 MB) e leva dezenas de segundos. Ele só executa quando a variável
RODAR_TESTES_DE_NAVEGADOR=1 está definida. Sem ela, o teste é pulado e a suíte
do dia a dia continua rápida.

    python -m playwright install chromium
    set RODAR_TESTES_DE_NAVEGADOR=1        # PowerShell: $env:RODAR_TESTES_DE_NAVEGADOR=1
    python manage.py test apps.atendimento.tests.test_navegador

As capturas de tela do README são geradas por esta execução, em docs/capturas/.
Elas são reais por construção: se a tela quebrar, o teste falha antes de
salvar a imagem.
"""
import os
import unittest
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from apps.atendimento import perfis
from apps.atendimento.models import Comanda, Mesa, Pagamento
from apps.cardapio.models import Adicional, Categoria, Produto

# O Playwright síncrono conversa com o Django a partir de outro contexto de
# execução; sem isto o ORM recusa a chamada por achar que é código assíncrono.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

try:
    from playwright.sync_api import expect, sync_playwright
except ImportError:  # playwright não instalado: o teste é pulado
    sync_playwright = None
    expect = None

SENHA = 'senha-de-navegador-123'
CAPTURAS = Path(settings.BASE_DIR) / 'docs' / 'capturas'

CELULAR = {'width': 390, 'height': 844}
DESKTOP = {'width': 1366, 'height': 900}

DEVE_RODAR = os.environ.get('RODAR_TESTES_DE_NAVEGADOR') == '1'


@unittest.skipUnless(DEVE_RODAR, 'defina RODAR_TESTES_DE_NAVEGADOR=1 para rodar')
@unittest.skipIf(sync_playwright is None, 'playwright não está instalado')
class FluxoDeAtendimentoNoNavegador(StaticLiveServerTestCase):
    """Abrir mesa → lançar → enviar → caixa → pagar → histórico → nova comanda."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        CAPTURAS.mkdir(parents=True, exist_ok=True)
        cls.playwright = sync_playwright().start()
        cls.navegador = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        perfis.sincronizar_grupos()

        self.garcom = self._usuario('garcom_nav', perfis.GARCOM)
        self.caixa = self._usuario('caixa_nav', perfis.CAIXA)

        for numero in range(1, 9):
            Mesa.objects.create(numero=numero)

        lanches = Categoria.objects.create(nome='Lanches', ordem=10)
        pizzas = Categoria.objects.create(nome='Pizzas', ordem=20)
        bebidas = Categoria.objects.create(nome='Bebidas', ordem=30)

        Produto.objects.create(
            categoria=lanches,
            nome='X-Salada',
            descricao='Pão, hambúrguer, queijo, alface e tomate',
            preco=Decimal('26.00'),
        )
        Produto.objects.create(
            categoria=bebidas, nome='Refrigerante lata', preco=Decimal('7.00')
        )
        Produto.objects.create(
            categoria=pizzas,
            nome='Pizza Marguerita',
            preco=Decimal('55.00'),
            permite_meio_a_meio=True,
        )
        Produto.objects.create(
            categoria=pizzas,
            nome='Pizza Portuguesa',
            preco=Decimal('62.00'),
            permite_meio_a_meio=True,
        )

        bacon = Adicional.objects.create(nome='Bacon extra', preco=Decimal('6.00'))
        bacon.categorias.set([lanches])

        self.erros_de_console = []

    @staticmethod
    def _usuario(username, grupo):
        usuario = User.objects.create_user(username=username, password=SENHA)
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    # -- apoio --------------------------------------------------------------
    def _abrir_pagina(self, tamanho, rotulo):
        contexto = self.navegador.new_context(viewport=tamanho)
        pagina = contexto.new_page()
        pagina.on(
            'console',
            lambda msg: self.erros_de_console.append(f'[{rotulo}] {msg.text}')
            if msg.type == 'error'
            else None,
        )
        pagina.on(
            'pageerror',
            lambda erro: self.erros_de_console.append(f'[{rotulo}] pageerror: {erro}'),
        )
        return contexto, pagina

    def _entrar(self, pagina, usuario):
        pagina.goto(f'{self.live_server_url}/entrar/')
        pagina.fill('#id_username', usuario.username)
        pagina.fill('#id_password', SENHA)
        pagina.click('button[type="submit"]')
        pagina.wait_for_load_state('networkidle')

    def _lancar_item(self, pagina, categoria, produto, quantidade=1,
                     adicional=None, observacao=None, segundo_sabor=None):
        pagina.click(f'#categorias button:text-is("{categoria}")')
        pagina.wait_for_selector('#dialogo-item[open]')

        pagina.click(f'#lista-produtos .opcao:has-text("{produto}")')

        if segundo_sabor:
            pagina.wait_for_selector('#bloco-meio-a-meio:visible')
            pagina.click(f'#lista-segundo-sabor .opcao:has-text("{segundo_sabor}")')

        if adicional:
            pagina.click(f'#lista-adicionais .opcao:has-text("{adicional}")')

        if quantidade != 1:
            pagina.fill('#quantidade-item', str(quantidade))

        if observacao:
            pagina.fill('#observacao-item', observacao)

        pagina.click('#botao-adicionar-rascunho')
        pagina.wait_for_selector('#dialogo-item[open]', state='detached', timeout=5000)

    # -- o teste ------------------------------------------------------------
    def test_jornada_completa_do_garcom_ao_caixa(self):
        contexto_garcom, garcom = self._abrir_pagina(CELULAR, 'garçom')
        contexto_caixa, caixa = self._abrir_pagina(DESKTOP, 'caixa')

        try:
            # ---------- 1. o garçom entra e abre a mesa 5 ----------
            self._entrar(garcom, self.garcom)
            expect(garcom).to_have_url(f'{self.live_server_url}/atendimento/comanda/')

            garcom.click('.mesa[data-mesa="5"]')
            garcom.wait_for_selector('#secao-comanda', state='visible')
            expect(garcom.locator('#identificacao-comanda')).to_contain_text('Comanda #')

            comanda = Comanda.objects.get(mesa__numero=5)
            self.assertTrue(comanda.esta_aberta)

            # ---------- 2. monta o rascunho ----------
            self._lancar_item(
                garcom, 'Lanches', 'X-Salada',
                quantidade=2, adicional='Bacon extra', observacao='sem cebola',
            )
            self._lancar_item(garcom, 'Bebidas', 'Refrigerante lata')

            expect(garcom.locator('#itens-rascunho li')).to_have_count(2)
            # Nada disso está no servidor ainda.
            self.assertEqual(comanda.itens.count(), 0)

            garcom.screenshot(path=str(CAPTURAS / '01-garcom-rascunho.png'))

            # ---------- 3. remove e recoloca: rascunho é livre ----------
            garcom.click('#itens-rascunho li:last-child button')
            expect(garcom.locator('#itens-rascunho li')).to_have_count(1)
            self._lancar_item(garcom, 'Bebidas', 'Refrigerante lata')
            expect(garcom.locator('#itens-rascunho li')).to_have_count(2)

            # ---------- 4. envia ----------
            garcom.click('#botao-enviar')
            garcom.wait_for_selector('#mensagem-comanda .aviso--ok')
            expect(garcom.locator('#itens-enviados li')).to_have_count(2)
            expect(garcom.locator('#itens-rascunho li')).to_have_count(0)

            comanda.refresh_from_db()
            # (26,00 + 6,00) x 2 + 7,00 = 71,00 — calculado pelo servidor
            self.assertEqual(comanda.total(), Decimal('71.00'))
            self.assertEqual(comanda.itens.count(), 2)
            expect(garcom.locator('#total-geral')).to_contain_text('71,00')

            garcom.screenshot(path=str(CAPTURAS / '02-garcom-enviado.png'))

            # ---------- 5. o caixa vê, sem recarregar nem relogar ----------
            self._entrar(caixa, self.caixa)
            expect(caixa).to_have_url(f'{self.live_server_url}/atendimento/caixa/')

            caixa.click('#botao-atualizar')
            caixa.wait_for_selector('.mesa[data-mesa="5"].mesa--ocupada')
            expect(caixa.locator('.mesa[data-mesa="5"]')).to_contain_text('71,00')

            caixa.click('.mesa[data-mesa="5"]')
            caixa.wait_for_selector('#painel-comanda', state='visible')
            expect(caixa.locator('#lista-itens-comanda li')).to_have_count(2)
            expect(caixa.locator('#lista-itens-comanda')).to_contain_text('sem cebola')
            expect(caixa.locator('#total-comanda')).to_contain_text('71,00')

            caixa.screenshot(path=str(CAPTURAS / '03-caixa-comanda.png'))

            # ---------- 6. segunda rodada, com meio a meio ----------
            self._lancar_item(
                garcom, 'Pizzas', 'Pizza Marguerita', segundo_sabor='Pizza Portuguesa'
            )
            garcom.click('#botao-enviar')
            garcom.wait_for_selector('#mensagem-comanda .aviso--ok')

            comanda.refresh_from_db()
            # Meio a meio cobra o sabor mais caro: 71,00 + 62,00 = 133,00
            self.assertEqual(comanda.total(), Decimal('133.00'))
            self.assertEqual(comanda.itens.count(), 3)

            # A rodada anterior não foi reenviada.
            descricoes = list(comanda.itens.values_list('descricao', flat=True))
            self.assertEqual(descricoes.count('X-Salada'), 1)
            self.assertEqual(descricoes.count('Refrigerante lata'), 1)

            # O caixa acompanha a inclusão feita pelo outro usuário.
            caixa.click('#botao-atualizar')
            expect(caixa.locator('#total-comanda')).to_contain_text('133,00')
            expect(caixa.locator('#lista-itens-comanda li')).to_have_count(3)
            expect(caixa.locator('#lista-itens-comanda')).to_contain_text('Meio a meio')

            # ---------- 7. recarregar não perde nem duplica ----------
            garcom.reload()
            garcom.click('.mesa[data-mesa="5"]')
            garcom.wait_for_selector('#secao-comanda', state='visible')
            expect(garcom.locator('#itens-enviados li')).to_have_count(3)
            expect(garcom.locator('#total-geral')).to_contain_text('133,00')

            comanda.refresh_from_db()
            self.assertEqual(comanda.itens.count(), 3)

            # ---------- 8. pagamento em dinheiro ----------
            caixa.click('#botao-abrir-pagamento')
            caixa.wait_for_selector('#dialogo-pagamento[open]')
            caixa.select_option('#meio-pagamento', 'dinheiro')
            caixa.fill('#valor-recebido', '150')
            expect(caixa.locator('#troco-previsto')).to_contain_text('17,00')

            caixa.screenshot(path=str(CAPTURAS / '04-caixa-pagamento.png'))

            caixa.click('#botao-confirmar-pagamento')
            caixa.wait_for_selector('#mensagem-geral .aviso--ok')

            pagamento = Pagamento.objects.get(comanda=comanda)
            self.assertEqual(pagamento.valor, Decimal('133.00'))
            self.assertEqual(pagamento.troco, Decimal('17.00'))
            self.assertEqual(pagamento.registrado_por, self.caixa)

            comanda.refresh_from_db()
            self.assertEqual(comanda.status, Comanda.Status.PAGA)

            # ---------- 9. a mesa fica livre ----------
            caixa.click('#botao-atualizar')
            caixa.wait_for_selector('.mesa[data-mesa="5"].mesa--livre')

            # ---------- 10. histórico ----------
            caixa.goto(f'{self.live_server_url}/atendimento/historico/')
            expect(caixa.locator('body')).to_contain_text('R$ 133,00')
            expect(caixa.locator('body')).to_contain_text('Paga')
            caixa.screenshot(
                path=str(CAPTURAS / '05-caixa-historico.png'), full_page=True
            )

            # ---------- 11. novo atendimento na mesma mesa ----------
            garcom.click('#botao-trocar-mesa')
            garcom.wait_for_selector('#secao-mesa', state='visible')
            garcom.click('.mesa[data-mesa="5"]')
            garcom.wait_for_selector('#secao-comanda', state='visible')
            expect(garcom.locator('#itens-enviados li')).to_have_count(0)
            expect(garcom.locator('#total-geral')).to_contain_text('0,00')

            nova = Comanda.objects.filter(mesa__numero=5).exclude(pk=comanda.pk).get()
            self.assertTrue(nova.esta_aberta)
            self.assertEqual(nova.itens.count(), 0)
            # O histórico anterior continua intacto.
            self.assertEqual(comanda.itens.count(), 3)

            # ---------- 12. console limpo ----------
            self.assertEqual(
                self.erros_de_console,
                [],
                'o navegador registrou erros durante o fluxo',
            )
        finally:
            contexto_garcom.close()
            contexto_caixa.close()

    def test_garcom_nao_ve_acoes_do_caixa(self):
        """A interface esconde o que o perfil não pode fazer.

        Complementa os testes de permissão: lá o servidor recusa; aqui a tela
        sequer oferece.
        """
        contexto, pagina = self._abrir_pagina(DESKTOP, 'garçom-no-caixa')
        try:
            self._entrar(pagina, self.garcom)
            pagina.goto(f'{self.live_server_url}/atendimento/caixa/')

            expect(pagina.locator('#botao-abrir-pagamento')).to_have_count(0)
            expect(pagina.locator('#botao-cancelar-comanda')).to_have_count(0)
            expect(pagina.locator('body')).to_contain_text('não registra pagamento')

            # O link do histórico também não aparece para ele.
            expect(pagina.locator('nav a[href*="historico"]')).to_have_count(0)
        finally:
            contexto.close()
