from django.urls import path
from .views import CaixaView, ComandaView
from . import api_views

app_name = 'funcionarios'

urlpatterns = [
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('comanda/', ComandaView.as_view(), name='comanda'),
    path('api/fechar_pedido/<int:pk>/', api_views.fechar_pedido, name='fechar_pedido'),
]
