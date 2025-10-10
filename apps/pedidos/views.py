from symtable import Class
from tempfile import template

from django.views.generic import TemplateView
from .models import Pizza, Extra, Refrigerante, Cerveja, Sobremesa, Borda, Pedido


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pizzas'] = Pizza.objects.all()
        context['extras'] = Extra.objects.all()
        context['refrigerantes'] = Refrigerante.objects.all()
        context['cervejas'] = Cerveja.objects.all()
        context['sobremesas'] = Sobremesa.objects.all()
        context['bordas'] = Borda.objects.all()
        return context


class CheckoutView(TemplateView):
    template_name = 'checkout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class CardapioView(TemplateView):
    template_name = 'cardapio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pizzas'] = Pizza.objects.all()
        context['extras'] = Extra.objects.all()
        context['refrigerantes'] = Refrigerante.objects.all()
        context['cervejas'] = Cerveja.objects.all()
        context['sobremesas'] = Sobremesa.objects.all()
        context['bordas'] = Borda.objects.all()
        return context


class CaixaView(TemplateView):
    template_name = 'caixa.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mesas'] = Pedido.objects.all()
        context['itens'] = Pedido.objects.all()
        context['total'] = Pedido.objects.all()
        context['status'] = Pedido.objects.all()

        return context


class ComandaView(TemplateView):
    template_name = 'caixa.html'
