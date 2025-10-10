from django.urls import path

from .views import IndexView, Cardapio

app_name = 'clientes'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('cardapio/', Cardapio.as_view(), name='cardapio'),
]
