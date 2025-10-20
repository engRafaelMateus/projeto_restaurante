from django.contrib import admin
from .models import Funcionario, Mesa, Pedido, ConfiguracaoMesas



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
