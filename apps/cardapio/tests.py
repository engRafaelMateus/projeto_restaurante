"""Regras do catálogo."""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Adicional, Categoria, Produto


class RegrasDoCatalogo(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lanches = Categoria.objects.create(nome='Lanches')
        cls.bebidas = Categoria.objects.create(nome='Bebidas')
        cls.xsalada = Produto.objects.create(
            categoria=cls.lanches, nome='X-Salada', preco=Decimal('26.00')
        )

    def test_slug_e_gerado_a_partir_do_nome(self):
        categoria = Categoria.objects.create(nome='Sobremesas Especiais')
        self.assertEqual(categoria.slug, 'sobremesas-especiais')

    def test_nome_de_produto_e_unico_dentro_da_categoria(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Produto.objects.create(
                    categoria=self.lanches, nome='X-Salada', preco=Decimal('30.00')
                )

    def test_mesmo_nome_em_categorias_diferentes_e_permitido(self):
        Produto.objects.create(categoria=self.bebidas, nome='X-Salada', preco=Decimal('30.00'))
        self.assertEqual(Produto.objects.filter(nome='X-Salada').count(), 2)

    def test_preco_zero_e_recusado_pelo_banco(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Produto.objects.create(
                    categoria=self.lanches, nome='Brinde', preco=Decimal('0.00')
                )

    def test_produto_inativo_sai_das_consultas_de_venda(self):
        self.xsalada.ativo = False
        self.xsalada.save()

        self.assertFalse(Produto.objects.vendaveis().filter(pk=self.xsalada.pk).exists())
        self.assertTrue(Produto.objects.filter(pk=self.xsalada.pk).exists())

    def test_produto_indisponivel_sai_das_consultas_de_venda(self):
        self.xsalada.disponivel = False
        self.xsalada.save()

        self.assertFalse(Produto.objects.vendaveis().filter(pk=self.xsalada.pk).exists())

    def test_categoria_inativa_tira_os_produtos_da_venda(self):
        self.lanches.ativo = False
        self.lanches.save()

        self.assertFalse(Produto.objects.vendaveis().filter(pk=self.xsalada.pk).exists())

    def test_adicionais_permitidos_seguem_a_categoria_do_produto(self):
        bacon = Adicional.objects.create(nome='Bacon extra', preco=Decimal('6.00'))
        bacon.categorias.set([self.lanches])
        gelo = Adicional.objects.create(nome='Gelo e limão', preco=Decimal('2.00'))
        gelo.categorias.set([self.bebidas])

        permitidos = list(self.xsalada.adicionais_permitidos())

        self.assertIn(bacon, permitidos)
        self.assertNotIn(gelo, permitidos)


class CardapioPublico(TestCase):
    def test_pagina_abre_sem_login(self):
        categoria = Categoria.objects.create(nome='Pizzas')
        Produto.objects.create(categoria=categoria, nome='Marguerita', preco=Decimal('55.00'))

        resposta = self.client.get(reverse('cardapio:publico'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Marguerita')
        self.assertContains(resposta, 'R$ 55,00')

    def test_produto_indisponivel_nao_aparece(self):
        categoria = Categoria.objects.create(nome='Pizzas')
        Produto.objects.create(
            categoria=categoria, nome='Esgotada', preco=Decimal('55.00'), disponivel=False
        )

        resposta = self.client.get(reverse('cardapio:publico'))

        self.assertNotContains(resposta, 'Esgotada')

    def test_cardapio_vazio_mostra_estado_vazio(self):
        resposta = self.client.get(reverse('cardapio:publico'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'ainda não tem produtos')
