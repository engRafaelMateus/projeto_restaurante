from django.urls import path

from . import api
from .views import CaixaView, ComandaView, HistoricoView

app_name = 'atendimento'

urlpatterns = [
    # Telas
    path('comanda/', ComandaView.as_view(), name='comanda'),
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('historico/', HistoricoView.as_view(), name='historico'),

    # API de leitura
    path('api/catalogo/', api.catalogo, name='api_catalogo'),
    path('api/estado/', api.estado_do_salao, name='api_estado'),
    path('api/comandas/<int:comanda_id>/', api.detalhe_da_comanda, name='api_comanda'),
    path(
        'api/mesas/<int:numero_da_mesa>/comanda/',
        api.comanda_aberta_da_mesa,
        name='api_comanda_da_mesa',
    ),

    # API de escrita
    path('api/comandas/abrir/', api.abrir_comanda, name='api_abrir_comanda'),
    path('api/comandas/<int:comanda_id>/itens/', api.enviar_itens, name='api_enviar_itens'),
    path(
        'api/comandas/<int:comanda_id>/pagamento/',
        api.registrar_pagamento,
        name='api_registrar_pagamento',
    ),
    path(
        'api/comandas/<int:comanda_id>/cancelar/',
        api.cancelar_comanda,
        name='api_cancelar_comanda',
    ),
    path('api/itens/<int:item_id>/cancelar/', api.cancelar_item, name='api_cancelar_item'),
]
