from django.urls import path
from .views import CaixaView, ComandaView
from . import api_views

app_name = 'funcionarios'

urlpatterns = [
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('comanda/', ComandaView.as_view(), name='comanda'),

    # Garçom - endpoints usados no JS
    path('api/abrir_mesa/', api_views.abrir_mesa, name='abrir_mesa'),
    path('api/listar_categorias/', api_views.listar_categorias, name='listar_categorias'),
    path('api/listar_itens/<int:categoria_id>/', api_views.listar_itens, name='listar_itens'),
    path('api/adicionar_item/', api_views.adicionar_item, name='adicionar_item'),
    path('api/enviar_pedido/', api_views.enviar_pedido, name='enviar_pedido'),
    path('api/pedido_aberto/<int:mesa_num>/', api_views.pedido_aberto, name='pedido_aberto'),

    # Caixa
    path('api/fechar_pedido/<int:pk>/', api_views.fechar_pedido, name='fechar_pedido'),
]
