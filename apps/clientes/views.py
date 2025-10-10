from django.views.generic import TemplateView
from apps.pedidos.models import Pizza, Extra

class IndexView(TemplateView):
    template_name =  'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pizzas'] = Pizza.objects.all()
        context['extras'] = Extra.objects.all()
        return context

class Cardapio(TemplateView):
    template_name =  'cardapio.html'





