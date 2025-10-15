from django.contrib import admin
from django.contrib.auth.models import Group
from django.urls import path
from django.shortcuts import redirect
from django.contrib.admin import AdminSite
from .models import Funcionario, Mesa, Pedido, ConfiguracaoMesas

# ---------- Redirecionamento automático ----------

class MyAdminSite(AdminSite):
    def login(self, request, extra_context=None):
        response = super().login(request, extra_context)
        if request.user.is_authenticated:
            if request.user.groups.filter(name='GrupoCaixa').exists():
                return redirect('/funcionarios/caixa/')
            elif request.user.groups.filter(name='GrupoGarcom').exists():
                return redirect('/funcionarios/comanda/')
        return response

# Registrar o AdminSite personalizado
admin_site = MyAdminSite(name='myadmin')

# ---------- Registro dos modelos ----------

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'login', 'ativo', 'criado', 'modificado')

@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'status')
    ordering = ['numero']

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('mesa', 'total', 'status')

@admin.register(ConfiguracaoMesas)
class ConfiguracaoMesasAdmin(admin.ModelAdmin):
    list_display = ('quantidade_mesas',)

    def save_model(self, request, obj, form, change):
        """Ao salvar, cria/remove mesas automaticamente"""
        super().save_model(request, obj, form, change)

        from .models import Mesa

        total = obj.quantidade_mesas
        atuais = Mesa.objects.count()

        # Criar mesas que faltam
        for i in range(atuais + 1, total + 1):
            Mesa.objects.create(numero=i, status='livre')

        # Remover mesas a mais
        if atuais > total:
            Mesa.objects.filter(numero__gt=total).delete()
