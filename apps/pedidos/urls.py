from django.urls import path

from .views import CheckoutView, CardapioView, CaixaView, ComandaView

app_name = 'pedidos'

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('cardapio/', CardapioView.as_view(), name='cardapio'),
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('comanda/', ComandaView.as_view(), name='comanda'),

]