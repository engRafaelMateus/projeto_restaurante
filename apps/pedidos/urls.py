from django.urls import path

from .views import CheckoutView, CardapioView

app_name = 'pedidos'

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('cardapio/', CardapioView.as_view(), name='cardapio'),

]