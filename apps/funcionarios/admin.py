from django.contrib import admin
from django.contrib.auth.models import Group
from django.urls import path
from django.shortcuts import redirect
from django.contrib.admin import AdminSite
from .models import Funcionario, Mesa, Pedido

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

@admin.register(Funcionario, site=admin_site)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'login', 'ativo', 'criado', 'modificado')

@admin.register(Mesa, site=admin_site)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'status')

@admin.register(Pedido, site=admin_site)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('mesa', 'itens', 'total', 'status')
