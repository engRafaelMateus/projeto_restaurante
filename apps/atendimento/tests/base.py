"""Apoio comum aos testes: usuários com perfil real e catálogo mínimo."""
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase

from apps.atendimento import perfis
from apps.atendimento.models import Mesa
from apps.cardapio.models import Adicional, Categoria, Produto

SENHA = 'senha-de-teste-123'


class CenarioBase(TestCase):
    """Monta um restaurante pequeno, porém completo, para cada teste."""

    @classmethod
    def setUpTestData(cls):
        perfis.sincronizar_grupos()

        cls.garcom = cls.criar_usuario('garcom_teste', perfis.GARCOM)
        cls.outro_garcom = cls.criar_usuario('garcom_dois', perfis.GARCOM)
        cls.caixa = cls.criar_usuario('caixa_teste', perfis.CAIXA)
        cls.gerente = cls.criar_usuario('gerente_teste', perfis.ADMINISTRACAO)

        cls.mesa5 = Mesa.objects.create(numero=5)
        cls.mesa6 = Mesa.objects.create(numero=6)

        cls.lanches = Categoria.objects.create(nome='Lanches', ordem=10)
        cls.pizzas = Categoria.objects.create(nome='Pizzas', ordem=20)
        cls.bebidas = Categoria.objects.create(nome='Bebidas', ordem=30)

        cls.xsalada = Produto.objects.create(
            categoria=cls.lanches, nome='X-Salada', preco=Decimal('26.00')
        )
        cls.xbacon = Produto.objects.create(
            categoria=cls.lanches, nome='X-Bacon', preco=Decimal('32.50')
        )
        cls.refrigerante = Produto.objects.create(
            categoria=cls.bebidas, nome='Refrigerante lata', preco=Decimal('7.00')
        )
        cls.pizza_barata = Produto.objects.create(
            categoria=cls.pizzas,
            nome='Pizza Marguerita',
            preco=Decimal('55.00'),
            permite_meio_a_meio=True,
        )
        cls.pizza_cara = Produto.objects.create(
            categoria=cls.pizzas,
            nome='Pizza Portuguesa',
            preco=Decimal('62.00'),
            permite_meio_a_meio=True,
        )
        cls.produto_inativo = Produto.objects.create(
            categoria=cls.lanches, nome='Fora de linha', preco=Decimal('10.00'), ativo=False
        )
        cls.produto_indisponivel = Produto.objects.create(
            categoria=cls.lanches, nome='Acabou hoje', preco=Decimal('15.00'), disponivel=False
        )

        cls.bacon_extra = Adicional.objects.create(nome='Bacon extra', preco=Decimal('6.00'))
        cls.bacon_extra.categorias.set([cls.lanches])

        cls.gelo_limao = Adicional.objects.create(nome='Gelo e limão', preco=Decimal('2.00'))
        cls.gelo_limao.categorias.set([cls.bebidas])

        cls.adicional_indisponivel = Adicional.objects.create(
            nome='Adicional esgotado', preco=Decimal('3.00'), disponivel=False
        )
        cls.adicional_indisponivel.categorias.set([cls.lanches])

    @staticmethod
    def criar_usuario(username, grupo):
        usuario = User.objects.create_user(username=username, password=SENHA)
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    # -- atalhos -----------------------------------------------------------
    def autenticar(self, usuario):
        self.assertTrue(self.client.login(username=usuario.username, password=SENHA))

    @staticmethod
    def item(produto, quantidade=1, adicionais=None, observacao='', segundo_sabor=None):
        return {
            'produto_id': produto.pk,
            'quantidade': quantidade,
            'adicionais': [a.pk for a in (adicionais or [])],
            'observacao': observacao,
            'produto_secundario_id': segundo_sabor.pk if segundo_sabor else None,
        }
