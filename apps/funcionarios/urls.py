from django.urls import path
from .views import CaixaView, ComandaView

app_name = 'funcionarios'

urlpatterns = [
    path('caixa/', CaixaView.as_view(), name='caixa'),
    path('comanda/', ComandaView.as_view(), name='comanda'),
]
