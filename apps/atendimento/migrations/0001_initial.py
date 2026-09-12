"""Migração inicial da operação de salão."""
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cardapio', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Mesa',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('numero', models.PositiveSmallIntegerField(unique=True, verbose_name='Número')),
                ('lugares', models.PositiveSmallIntegerField(default=4, verbose_name='Lugares')),
                (
                    'ativa',
                    models.BooleanField(
                        default=True,
                        help_text='Desmarque para tirar a mesa de operação sem apagar o histórico.',
                        verbose_name='Ativa',
                    ),
                ),
                ('criada_em', models.DateTimeField(auto_now_add=True, verbose_name='Criada em')),
            ],
            options={
                'verbose_name': 'Mesa',
                'verbose_name_plural': 'Mesas',
                'ordering': ['numero'],
            },
        ),
        migrations.CreateModel(
            name='Comanda',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[('aberta', 'Aberta'), ('paga', 'Paga'), ('cancelada', 'Cancelada')],
                        default='aberta',
                        max_length=10,
                        verbose_name='Situação',
                    ),
                ),
                ('aberta_em', models.DateTimeField(auto_now_add=True, verbose_name='Aberta em')),
                ('encerrada_em', models.DateTimeField(blank=True, null=True, verbose_name='Encerrada em')),
                (
                    'motivo_cancelamento',
                    models.CharField(blank=True, max_length=200, verbose_name='Motivo do cancelamento'),
                ),
                (
                    'aberta_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='comandas_abertas',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Aberta por',
                    ),
                ),
                (
                    'encerrada_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='comandas_encerradas',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Encerrada por',
                    ),
                ),
                (
                    'mesa',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='comandas',
                        to='atendimento.mesa',
                        verbose_name='Mesa',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Comanda',
                'verbose_name_plural': 'Comandas',
                'ordering': ['-aberta_em'],
                'permissions': [
                    ('lancar_itens', 'Pode abrir comanda e lançar itens'),
                    ('cancelar_item', 'Pode cancelar item já enviado'),
                    ('registrar_pagamento', 'Pode registrar pagamento e encerrar comanda'),
                    ('ver_historico_financeiro', 'Pode consultar o histórico financeiro'),
                ],
            },
        ),
        migrations.CreateModel(
            name='Envio',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('referencia', models.UUIDField(unique=True, verbose_name='Referência do envio')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Enviado em')),
                (
                    'comanda',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='envios',
                        to='atendimento.comanda',
                        verbose_name='Comanda',
                    ),
                ),
                (
                    'criado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='envios',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Enviado por',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Envio',
                'verbose_name_plural': 'Envios',
                'ordering': ['criado_em'],
            },
        ),
        migrations.CreateModel(
            name='ItemComanda',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('descricao', models.CharField(max_length=180, verbose_name='Descrição praticada')),
                (
                    'preco_unitario',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                        verbose_name='Preço unitário praticado',
                    ),
                ),
                (
                    'preco_adicionais',
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal('0.00'),
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                        verbose_name='Adicionais por unidade',
                    ),
                ),
                (
                    'adicionais_detalhe',
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Lista de {id, nome, preco} no momento da venda. Retrato, não relação viva.',
                        verbose_name='Adicionais praticados',
                    ),
                ),
                (
                    'quantidade',
                    models.PositiveSmallIntegerField(
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name='Quantidade',
                    ),
                ),
                ('observacao', models.CharField(blank=True, max_length=140, verbose_name='Observação')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Lançado em')),
                ('cancelado_em', models.DateTimeField(blank=True, null=True, verbose_name='Cancelado em')),
                (
                    'motivo_cancelamento',
                    models.CharField(blank=True, max_length=200, verbose_name='Motivo do cancelamento'),
                ),
                (
                    'cancelado_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens_cancelados',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Cancelado por',
                    ),
                ),
                (
                    'comanda',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='itens',
                        to='atendimento.comanda',
                        verbose_name='Comanda',
                    ),
                ),
                (
                    'criado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens_lancados',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Lançado por',
                    ),
                ),
                (
                    'envio',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens',
                        to='atendimento.envio',
                        verbose_name='Envio',
                    ),
                ),
                (
                    'produto',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens_vendidos',
                        to='cardapio.produto',
                        verbose_name='Produto',
                    ),
                ),
                (
                    'produto_secundario',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='itens_vendidos_como_segundo_sabor',
                        to='cardapio.produto',
                        verbose_name='Segundo sabor',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Item da comanda',
                'verbose_name_plural': 'Itens da comanda',
                'ordering': ['criado_em', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Pagamento',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'valor',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                        verbose_name='Valor da conta',
                    ),
                ),
                (
                    'meio',
                    models.CharField(
                        choices=[
                            ('dinheiro', 'Dinheiro'),
                            ('pix', 'Pix (registro manual)'),
                            ('debito', 'Cartão de débito (registro manual)'),
                            ('credito', 'Cartão de crédito (registro manual)'),
                        ],
                        max_length=10,
                        verbose_name='Meio de pagamento',
                    ),
                ),
                (
                    'valor_recebido',
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        verbose_name='Valor recebido em dinheiro',
                    ),
                ),
                (
                    'troco',
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Troco'
                    ),
                ),
                ('registrado_em', models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')),
                ('observacao', models.CharField(blank=True, max_length=200, verbose_name='Observação')),
                (
                    'comanda',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamento',
                        to='atendimento.comanda',
                        verbose_name='Comanda',
                    ),
                ),
                (
                    'registrado_por',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='pagamentos_registrados',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Registrado por',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Pagamento',
                'verbose_name_plural': 'Pagamentos',
                'ordering': ['-registrado_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='mesa',
            constraint=models.CheckConstraint(
                condition=models.Q(('numero__gt', 0)), name='mesa_numero_positivo'
            ),
        ),
        migrations.AddIndex(
            model_name='comanda',
            index=models.Index(fields=['status', '-aberta_em'], name='idx_comanda_status_data'),
        ),
        migrations.AddConstraint(
            model_name='comanda',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'aberta')),
                fields=('mesa',),
                name='unica_comanda_aberta_por_mesa',
            ),
        ),
        migrations.AddConstraint(
            model_name='comanda',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(('encerrada_em__isnull', True), ('status', 'aberta')),
                    models.Q(('encerrada_em__isnull', False), ('status__in', ['paga', 'cancelada'])),
                    _connector='OR',
                ),
                name='comanda_encerramento_coerente',
            ),
        ),
        migrations.AddIndex(
            model_name='itemcomanda',
            index=models.Index(fields=['comanda', 'cancelado_em'], name='idx_item_comanda_ativo'),
        ),
        migrations.AddConstraint(
            model_name='itemcomanda',
            constraint=models.CheckConstraint(
                condition=models.Q(('quantidade__gte', 1)), name='item_quantidade_positiva'
            ),
        ),
        migrations.AddConstraint(
            model_name='itemcomanda',
            constraint=models.CheckConstraint(
                condition=models.Q(('preco_unitario__gt', Decimal('0.00'))),
                name='item_preco_unitario_positivo',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemcomanda',
            constraint=models.CheckConstraint(
                condition=models.Q(('preco_adicionais__gte', Decimal('0.00'))),
                name='item_preco_adicionais_nao_negativo',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemcomanda',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ('cancelado_em__isnull', True),
                        ('cancelado_por__isnull', True),
                        ('motivo_cancelamento', ''),
                    ),
                    models.Q(('cancelado_em__isnull', False), ('cancelado_por__isnull', False)),
                    _connector='OR',
                ),
                name='item_cancelamento_coerente',
            ),
        ),
        migrations.AddIndex(
            model_name='pagamento',
            index=models.Index(fields=['-registrado_em'], name='idx_pagamento_data'),
        ),
        migrations.AddConstraint(
            model_name='pagamento',
            constraint=models.CheckConstraint(
                condition=models.Q(('valor__gt', Decimal('0.00'))), name='pagamento_valor_positivo'
            ),
        ),
        migrations.AddConstraint(
            model_name='pagamento',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ('troco__isnull', True), ('troco__gte', Decimal('0.00')), _connector='OR'
                ),
                name='pagamento_troco_nao_negativo',
            ),
        ),
        migrations.AddConstraint(
            model_name='pagamento',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ('meio', 'dinheiro'),
                        ('troco__isnull', False),
                        ('valor_recebido__isnull', False),
                    ),
                    models.Q(('meio', 'dinheiro'), _negated=True),
                    _connector='OR',
                ),
                name='pagamento_dinheiro_exige_recebido_e_troco',
            ),
        ),
    ]
