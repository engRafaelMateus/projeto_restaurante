from django.urls import path

from .views import CardapioPublicoView

app_name = 'cardapio'

urlpatterns = [
    path('', CardapioPublicoView.as_view(), name='publico'),
]
