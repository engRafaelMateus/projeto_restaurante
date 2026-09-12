"""
Operação de salão: mesas, comandas, itens, envios e pagamento.

Três decisões estruturais estão nestes modelos e valem uma leitura:

1. `Mesa` não guarda status. "Ocupada" é a existência de uma comanda aberta,
   consultada no banco. Estado duplicado é estado que diverge.

2. Só existe uma comanda aberta por mesa, e isso é garantido por
   `UniqueConstraint` com condição — no banco, não em um `if` antes do save.
   Duas requisições simultâneas não conseguem criar duas comandas.

3. `ItemComanda` guarda um retrato do que foi vendido (nome, preço unitário,
   adicionais) além da chave estrangeira para o produto. Mudar o preço do
   catálogo amanhã não altera a conta de hoje.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from apps.cardapio.models import Produto

from .valores import ZERO, dinheiro, formatar_brl


class Mesa(models.Model):
    numero = models.PositiveSmallIntegerField('Número', unique=True)
    lugares = models.PositiveSmallIntegerField('Lugares', default=4)
    ativa = models.BooleanField(
        'Ativa',
        default=True,
        help_text='Desmarque para tirar a mesa de operação sem apagar o histórico.',
    )
    criada_em = models.DateTimeField('Criada em', auto_now_add=True)

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(numero__gt=0), name='mesa_numero_positivo'
            ),
        ]

    def __str__(self):
        return f'Mesa {self.numero}'

    def comanda_aberta(self):
        """Comanda aberta desta mesa, ou None. Fonte única do estado da mesa."""
        return self.comandas.filter(status=Comanda.Status.ABERTA).first()

    @property
    def ocupada(self):
        return self.comandas.filter(status=Comanda.Status.ABERTA).exists()


class ComandaQuerySet(models.QuerySet):
    def abertas(self):
        return self.filter(status=Comanda.Status.ABERTA)

    def encerradas(self):
        return self.filter(status__in=[Comanda.Status.PAGA, Comanda.Status.CANCELADA])

    def com_totais(self):
        """Anota o total da comanda em uma única consulta, sem N+1.

        Soma apenas itens não cancelados: (preço + adicionais) x quantidade.
        """
        return self.annotate(
            total_calculado=Sum(
                (F('itens__preco_unitario') + F('itens__preco_adicionais'))
                * F('itens__quantidade'),
                filter=models.Q(itens__cancelado_em__isnull=True),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            )
        )


class Comanda(models.Model):
    """Conta de uma mesa, do momento em que ela é aberta até o pagamento."""

    class Status(models.TextChoices):
        ABERTA = 'aberta', 'Aberta'
        PAGA = 'paga', 'Paga'
        CANCELADA = 'cancelada', 'Cancelada'

    mesa = models.ForeignKey(
        Mesa, verbose_name='Mesa', on_delete=models.PROTECT, related_name='comandas'
    )
    status = models.CharField(
        'Situação', max_length=10, choices=Status.choices, default=Status.ABERTA
    )

    aberta_em = models.DateTimeField('Aberta em', auto_now_add=True)
    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Aberta por',
        on_delete=models.PROTECT,
        related_name='comandas_abertas',
        null=True,
        blank=True,
    )

    encerrada_em = models.DateTimeField('Encerrada em', null=True, blank=True)
    encerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Encerrada por',
        on_delete=models.PROTECT,
        related_name='comandas_encerradas',
        null=True,
        blank=True,
    )
    motivo_cancelamento = models.CharField(
        'Motivo do cancelamento', max_length=200, blank=True
    )

    objects = ComandaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Comanda'
        verbose_name_plural = 'Comandas'
        ordering = ['-aberta_em']
        constraints = [
            # No máximo uma comanda aberta por mesa — garantia do banco.
            models.UniqueConstraint(
                fields=['mesa'],
                condition=models.Q(status='aberta'),
                name='unica_comanda_aberta_por_mesa',
            ),
            # Comanda encerrada tem data de encerramento; comanda aberta, não.
            models.CheckConstraint(
                condition=(
                    models.Q(status='aberta', encerrada_em__isnull=True)
                    | models.Q(status__in=['paga', 'cancelada'], encerrada_em__isnull=False)
                ),
                name='comanda_encerramento_coerente',
            ),
        ]
        indexes = [
            models.Index(fields=['status', '-aberta_em'], name='idx_comanda_status_data'),
        ]
        permissions = [
            ('lancar_itens', 'Pode abrir comanda e lançar itens'),
            ('cancelar_item', 'Pode cancelar item já enviado'),
            ('registrar_pagamento', 'Pode registrar pagamento e encerrar comanda'),
            ('ver_historico_financeiro', 'Pode consultar o histórico financeiro'),
        ]

    def __str__(self):
        return f'Comanda #{self.pk} — Mesa {self.mesa.numero} ({self.get_status_display()})'

    # -- estado -------------------------------------------------------------
    @property
    def esta_aberta(self):
        return self.status == self.Status.ABERTA

    @property
    def itens_ativos(self):
        return self.itens.filter(cancelado_em__isnull=True)

    @property
    def esta_paga(self):
        return hasattr(self, 'pagamento')

    # -- valores ------------------------------------------------------------
    def total(self) -> Decimal:
        """Total devido: soma dos subtotais dos itens não cancelados.

        Arredonda por linha e depois soma, para que o total não dependa da
        ordem em que os itens foram lançados.
        """
        total = ZERO
        for item in self.itens_ativos:
            total += item.subtotal
        return dinheiro(total)

    @property
    def total_formatado(self):
        return formatar_brl(self.total())

    def resumo_json(self, incluir_cancelados=True):
        """Retrato da comanda usado pelas telas de garçom, caixa e histórico."""
        itens = self.itens.select_related('produto', 'criado_por', 'cancelado_por')
        if not incluir_cancelados:
            itens = itens.filter(cancelado_em__isnull=True)
        return {
            'id': self.pk,
            'mesa': self.mesa.numero,
            'status': self.status,
            'status_exibicao': self.get_status_display(),
            'aberta_em': timezone.localtime(self.aberta_em).isoformat(),
            'aberta_por': self.aberta_por.get_username() if self.aberta_por_id else None,
            'total': str(self.total()),
            'total_formatado': self.total_formatado,
            'paga': self.esta_paga,
            'itens': [item.resumo_json() for item in itens],
        }


class Envio(models.Model):
    """Uma tentativa de envio de itens do garçom para o servidor.

    A `referencia` é gerada pelo navegador antes do POST e é única no banco.
    Se a mesma tentativa chegar duas vezes — usuário clicou duas vezes, a rede
    caiu depois que o servidor gravou, o celular repetiu a requisição —, a
    segunda encontra o envio já existente e devolve o mesmo resultado, sem
    criar itens novos. É esta tabela que torna `enviar_itens` idempotente.
    """

    comanda = models.ForeignKey(
        Comanda, verbose_name='Comanda', on_delete=models.CASCADE, related_name='envios'
    )
    referencia = models.UUIDField('Referência do envio', unique=True)
    criado_em = models.DateTimeField('Enviado em', auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Enviado por',
        on_delete=models.PROTECT,
        related_name='envios',
    )

    class Meta:
        verbose_name = 'Envio'
        verbose_name_plural = 'Envios'
        ordering = ['criado_em']

    def __str__(self):
        return f'Envio {self.referencia} (comanda #{self.comanda_id})'


class ItemComanda(models.Model):
    """Um item lançado e persistido. Guarda o preço praticado na venda."""

    comanda = models.ForeignKey(
        Comanda, verbose_name='Comanda', on_delete=models.CASCADE, related_name='itens'
    )
    envio = models.ForeignKey(
        Envio, verbose_name='Envio', on_delete=models.PROTECT, related_name='itens'
    )

    produto = models.ForeignKey(
        Produto,
        verbose_name='Produto',
        on_delete=models.PROTECT,
        related_name='itens_vendidos',
    )
    produto_secundario = models.ForeignKey(
        Produto,
        verbose_name='Segundo sabor',
        on_delete=models.PROTECT,
        related_name='itens_vendidos_como_segundo_sabor',
        null=True,
        blank=True,
    )

    # --- retrato histórico da venda ---------------------------------------
    descricao = models.CharField('Descrição praticada', max_length=180)
    preco_unitario = models.DecimalField(
        'Preço unitário praticado',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    preco_adicionais = models.DecimalField(
        'Adicionais por unidade',
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    adicionais_detalhe = models.JSONField(
        'Adicionais praticados',
        default=list,
        blank=True,
        help_text='Lista de {id, nome, preco} no momento da venda. Retrato, não relação viva.',
    )

    quantidade = models.PositiveSmallIntegerField(
        'Quantidade', validators=[MinValueValidator(1)]
    )
    observacao = models.CharField('Observação', max_length=140, blank=True)

    criado_em = models.DateTimeField('Lançado em', auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Lançado por',
        on_delete=models.PROTECT,
        related_name='itens_lancados',
    )

    cancelado_em = models.DateTimeField('Cancelado em', null=True, blank=True)
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Cancelado por',
        on_delete=models.PROTECT,
        related_name='itens_cancelados',
        null=True,
        blank=True,
    )
    motivo_cancelamento = models.CharField(
        'Motivo do cancelamento', max_length=200, blank=True
    )

    class Meta:
        verbose_name = 'Item da comanda'
        verbose_name_plural = 'Itens da comanda'
        ordering = ['criado_em', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=1), name='item_quantidade_positiva'
            ),
            models.CheckConstraint(
                condition=models.Q(preco_unitario__gt=Decimal('0.00')),
                name='item_preco_unitario_positivo',
            ),
            models.CheckConstraint(
                condition=models.Q(preco_adicionais__gte=Decimal('0.00')),
                name='item_preco_adicionais_nao_negativo',
            ),
            # Cancelamento só é válido com data, responsável e motivo juntos.
            models.CheckConstraint(
                condition=(
                    models.Q(
                        cancelado_em__isnull=True,
                        cancelado_por__isnull=True,
                        motivo_cancelamento='',
                    )
                    | models.Q(cancelado_em__isnull=False, cancelado_por__isnull=False)
                ),
                name='item_cancelamento_coerente',
            ),
        ]
        indexes = [
            models.Index(fields=['comanda', 'cancelado_em'], name='idx_item_comanda_ativo'),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.descricao}'

    @property
    def cancelado(self):
        return self.cancelado_em is not None

    @property
    def subtotal(self) -> Decimal:
        if self.cancelado:
            return ZERO
        return dinheiro(
            (dinheiro(self.preco_unitario) + dinheiro(self.preco_adicionais))
            * self.quantidade
        )

    def resumo_json(self):
        return {
            'id': self.pk,
            'descricao': self.descricao,
            'quantidade': self.quantidade,
            'preco_unitario': str(dinheiro(self.preco_unitario)),
            'preco_adicionais': str(dinheiro(self.preco_adicionais)),
            'adicionais': self.adicionais_detalhe or [],
            'observacao': self.observacao,
            'subtotal': str(self.subtotal),
            'subtotal_formatado': formatar_brl(self.subtotal),
            'cancelado': self.cancelado,
            'motivo_cancelamento': self.motivo_cancelamento,
            'lancado_por': self.criado_por.get_username() if self.criado_por_id else None,
            'lancado_em': timezone.localtime(self.criado_em).isoformat()
            if self.criado_em
            else None,
            'envio_id': self.envio_id,
        }


class Pagamento(models.Model):
    """Liquidação integral e manual de uma comanda.

    OneToOne com a comanda: o próprio banco impede pagamento duplicado.
    Nenhum dado de cartão é armazenado — apenas o meio informado pelo operador.
    Registrar Pix ou cartão aqui **não** confirma transação financeira externa.
    """

    class Meio(models.TextChoices):
        DINHEIRO = 'dinheiro', 'Dinheiro'
        PIX = 'pix', 'Pix (registro manual)'
        DEBITO = 'debito', 'Cartão de débito (registro manual)'
        CREDITO = 'credito', 'Cartão de crédito (registro manual)'

    comanda = models.OneToOneField(
        Comanda, verbose_name='Comanda', on_delete=models.PROTECT, related_name='pagamento'
    )
    valor = models.DecimalField(
        'Valor da conta',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    meio = models.CharField('Meio de pagamento', max_length=10, choices=Meio.choices)
    valor_recebido = models.DecimalField(
        'Valor recebido em dinheiro', max_digits=10, decimal_places=2, null=True, blank=True
    )
    troco = models.DecimalField(
        'Troco', max_digits=10, decimal_places=2, null=True, blank=True
    )

    registrado_em = models.DateTimeField('Registrado em', auto_now_add=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Registrado por',
        on_delete=models.PROTECT,
        related_name='pagamentos_registrados',
    )
    observacao = models.CharField('Observação', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-registrado_em']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gt=Decimal('0.00')), name='pagamento_valor_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(troco__isnull=True) | models.Q(troco__gte=Decimal('0.00')),
                name='pagamento_troco_nao_negativo',
            ),
            # Em dinheiro exigimos valor recebido e troco; nos demais meios, não.
            models.CheckConstraint(
                condition=(
                    models.Q(meio='dinheiro', valor_recebido__isnull=False, troco__isnull=False)
                    | ~models.Q(meio='dinheiro')
                ),
                name='pagamento_dinheiro_exige_recebido_e_troco',
            ),
        ]
        indexes = [
            models.Index(fields=['-registrado_em'], name='idx_pagamento_data'),
        ]

    def __str__(self):
        return f'Pagamento {formatar_brl(self.valor)} ({self.get_meio_display()})'

    @property
    def confirma_transacao_externa(self):
        """Nunca. Existe para deixar isso explícito em código e em tela."""
        return False
