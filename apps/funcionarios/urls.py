from django.urls import path

from apps.funcionarios.views import Lancar_Pedido, Caixa

app_name = 'funcionarios'

urlpatterns = [
    path('caixa/', Caixa.as_view(), name='caixa'),
    path('lancar_pedido/', Lancar_Pedido.as_view(), name='lancar'),
]