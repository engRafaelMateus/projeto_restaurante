from django.views.generic import TemplateView

class Lancar_Pedido(TemplateView):
    template_name =  'funcionarios/lancar_pedido.html'


class Caixa(TemplateView):
    template_name =  'funcionarios/caixa.html'

