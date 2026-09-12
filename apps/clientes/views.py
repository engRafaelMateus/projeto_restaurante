from django.views.generic import TemplateView

from apps.cardapio.models import Produto


class IndexView(TemplateView):
    """Página inicial pública do restaurante."""

    template_name = 'clientes/index.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['tela_atual'] = 'index'
        contexto['destaques'] = Produto.objects.para_cardapio()[:6]
        return contexto
