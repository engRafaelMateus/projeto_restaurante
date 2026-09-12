"""
Administração.

Decisões deliberadas aqui:

* Pagamento é somente leitura no admin. Histórico financeiro que pode ser
  editado livremente não é histórico.
* Item de comanda não é editável: cancelar item tem fluxo próprio, com motivo
  e responsável registrados.
"""
from django.contrib import admin

from .models import Comanda, Envio, ItemComanda, Mesa, Pagamento
from .valores import formatar_brl


class ItemComandaInline(admin.TabularInline):
    model = ItemComanda
    extra = 0
    can_delete = False
    fields = (
        'descricao',
        'quantidade',
        'preco_unitario',
        'preco_adicionais',
        'observacao',
        'criado_por',
        'cancelado_em',
        'motivo_cancelamento',
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'lugares', 'ativa', 'situacao')
    list_filter = ('ativa',)
    ordering = ('numero',)

    @admin.display(description='Situação', boolean=False)
    def situacao(self, obj):
        return 'Ocupada' if obj.ocupada else 'Livre'


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'mesa',
        'status',
        'total_exibido',
        'aberta_em',
        'aberta_por',
        'encerrada_em',
        'encerrada_por',
    )
    list_filter = ('status', 'mesa')
    list_select_related = ('mesa', 'aberta_por', 'encerrada_por')
    date_hierarchy = 'aberta_em'
    readonly_fields = (
        'aberta_em',
        'aberta_por',
        'encerrada_em',
        'encerrada_por',
        'total_exibido',
    )
    inlines = [ItemComandaInline]

    @admin.display(description='Total')
    def total_exibido(self, obj):
        return formatar_brl(obj.total())

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'comanda',
        'valor_exibido',
        'meio',
        'valor_recebido',
        'troco',
        'registrado_em',
        'registrado_por',
    )
    list_filter = ('meio',)
    list_select_related = ('comanda', 'comanda__mesa', 'registrado_por')
    date_hierarchy = 'registrado_em'
    search_fields = ('comanda__id',)

    @admin.display(description='Valor')
    def valor_exibido(self, obj):
        return formatar_brl(obj.valor)

    # Pagamento concluído não se edita nem se apaga pelo admin.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Envio)
class EnvioAdmin(admin.ModelAdmin):
    list_display = ('referencia', 'comanda', 'criado_em', 'criado_por', 'itens_do_envio')
    list_select_related = ('comanda', 'criado_por')
    readonly_fields = ('referencia', 'comanda', 'criado_em', 'criado_por')

    @admin.display(description='Itens')
    def itens_do_envio(self, obj):
        return obj.itens.count()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
