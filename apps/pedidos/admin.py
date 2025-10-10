from django.contrib import admin

from .models import Categoria, Extra, Pizza, Borda, Refrigerante, Cerveja, Sobremesa

# ----------------------------
# Categoria
# ----------------------------
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'criado', 'modificado')
    search_fields = ('categoria',)
    list_filter = ('ativo',)
    ordering = ('nome',)

# ----------------------------
# Extra
# ----------------------------
@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome', 'descricao')
    list_filter = ('ativo', 'categorias')
    filter_horizontal = ('categorias',)  # Para ManyToManyField ficar com caixa dupla
    ordering = ('nome',)

# ----------------------------
# pizza
# ----------------------------
@admin.register(Pizza)
class PizzaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome',)
    list_filter = ('categoria',)

# ----------------------------
# Borda
# ----------------------------
@admin.register(Borda)
class BordaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    ordering = ('nome',)


@admin.register(Refrigerante)
class RefrigeranteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    ordering = ('nome',)


@admin.register(Cerveja)
class CervejaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    ordering = ('nome',)


@admin.register(Sobremesa)
class SobremesaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'ativo', 'criado', 'modificado')
    search_fields = ('nome',)
    list_filter = ('ativo',)
    ordering = ('nome',)