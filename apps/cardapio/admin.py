from django.contrib import admin

from .models import Adicional, Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem', 'ativo', 'total_de_produtos', 'atualizado_em')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    ordering = ('ordem', 'nome')
    prepopulated_fields = {'slug': ('nome',)}

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(_produtos=Count('produtos'))

    @admin.display(description='Produtos', ordering='_produtos')
    def total_de_produtos(self, obj):
        return obj._produtos


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'categoria',
        'preco',
        'disponivel',
        'ativo',
        'permite_meio_a_meio',
        'atualizado_em',
    )
    list_filter = ('categoria', 'disponivel', 'ativo', 'permite_meio_a_meio')
    list_select_related = ('categoria',)
    search_fields = ('nome', 'descricao')
    list_editable = ('preco', 'disponivel')
    ordering = ('categoria__ordem', 'nome')
    fieldsets = (
        (None, {'fields': ('categoria', 'nome', 'descricao')}),
        ('Venda', {'fields': ('preco', 'disponivel', 'ativo', 'permite_meio_a_meio')}),
        ('Imagem', {'fields': ('imagem',), 'classes': ('collapse',)}),
    )


@admin.register(Adicional)
class AdicionalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'disponivel', 'ativo', 'categorias_exibidas')
    list_filter = ('disponivel', 'ativo', 'categorias')
    search_fields = ('nome',)
    filter_horizontal = ('categorias',)
    ordering = ('nome',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('categorias')

    @admin.display(description='Categorias')
    def categorias_exibidas(self, obj):
        return ', '.join(c.nome for c in obj.categorias.all()) or '—'
