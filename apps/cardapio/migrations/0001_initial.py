"""Migração inicial do catálogo."""
import django.core.validators
import django.db.models.deletion
from decimal import Decimal

from django.db import migrations, models

import apps.cardapio.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque para retirar do cadastro sem apagar o histórico de vendas.',
                        verbose_name='Ativo',
                    ),
                ),
                ('nome', models.CharField(max_length=60, unique=True, verbose_name='Nome')),
                (
                    'slug',
                    models.SlugField(
                        blank=True, max_length=70, unique=True, verbose_name='Identificador'
                    ),
                ),
                (
                    'ordem',
                    models.PositiveSmallIntegerField(
                        default=100,
                        help_text='Menor número aparece primeiro nas telas.',
                        verbose_name='Ordem de exibição',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Categoria',
                'verbose_name_plural': 'Categorias',
                'ordering': ['ordem', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='Adicional',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque para retirar do cadastro sem apagar o histórico de vendas.',
                        verbose_name='Ativo',
                    ),
                ),
                ('nome', models.CharField(max_length=60, verbose_name='Nome')),
                (
                    'preco',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                        verbose_name='Preço',
                    ),
                ),
                (
                    'disponivel',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque quando o adicional estiver temporariamente indisponível.',
                        verbose_name='Disponível',
                    ),
                ),
                (
                    'categorias',
                    models.ManyToManyField(
                        blank=True,
                        related_name='adicionais',
                        to='cardapio.categoria',
                        verbose_name='Categorias em que aparece',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Adicional',
                'verbose_name_plural': 'Adicionais',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Produto',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                (
                    'ativo',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque para retirar do cadastro sem apagar o histórico de vendas.',
                        verbose_name='Ativo',
                    ),
                ),
                ('nome', models.CharField(max_length=80, verbose_name='Nome')),
                ('descricao', models.CharField(blank=True, max_length=300, verbose_name='Descrição')),
                (
                    'preco',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                        verbose_name='Preço',
                    ),
                ),
                (
                    'disponivel',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque quando o item acabar; o produto continua cadastrado.',
                        verbose_name='Disponível hoje',
                    ),
                ),
                (
                    'permite_meio_a_meio',
                    models.BooleanField(
                        default=False,
                        help_text='Use em pizzas. A cobrança segue a regra definida em ATENDIMENTO_REGRA_MEIO_A_MEIO.',
                        verbose_name='Permite meio a meio',
                    ),
                ),
                (
                    'imagem',
                    models.ImageField(
                        blank=True,
                        upload_to='produtos/',
                        validators=[
                            django.core.validators.validate_image_file_extension,
                            apps.cardapio.models.validar_tamanho_da_imagem,
                        ],
                        verbose_name='Imagem',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='produtos',
                        to='cardapio.categoria',
                        verbose_name='Categoria',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Produto',
                'verbose_name_plural': 'Produtos',
                'ordering': ['categoria__ordem', 'nome'],
            },
        ),
        migrations.AddConstraint(
            model_name='adicional',
            constraint=models.UniqueConstraint(fields=('nome',), name='adicional_nome_unico'),
        ),
        migrations.AddConstraint(
            model_name='adicional',
            constraint=models.CheckConstraint(
                condition=models.Q(('preco__gte', Decimal('0.00'))),
                name='adicional_preco_nao_negativo',
            ),
        ),
        migrations.AddIndex(
            model_name='produto',
            index=models.Index(
                fields=['categoria', 'disponivel'], name='idx_produto_cat_disp'
            ),
        ),
        migrations.AddConstraint(
            model_name='produto',
            constraint=models.UniqueConstraint(
                fields=('categoria', 'nome'), name='produto_nome_unico_por_categoria'
            ),
        ),
        migrations.AddConstraint(
            model_name='produto',
            constraint=models.CheckConstraint(
                condition=models.Q(('preco__gt', Decimal('0.00'))), name='produto_preco_positivo'
            ),
        ),
    ]
