from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Mesa

# Decorators para verificar grupos
def grupo_caixa(user):
    return user.groups.filter(name='GrupoCaixa').exists()

def grupo_garcon(user):
    return user.groups.filter(name='GrupoGarcom').exists()

# Views
@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
@method_decorator(user_passes_test(grupo_caixa, login_url='/admin/'), name='dispatch')
class CaixaView(TemplateView):
    template_name = 'funcionarios/caixa.html'


@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
@method_decorator(user_passes_test(grupo_garcon, login_url='/admin/'), name='dispatch')
class ComandaView(TemplateView):
    template_name = 'funcionarios/comanda.html'



@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
@method_decorator(user_passes_test(grupo_caixa, login_url='/admin/'), name='dispatch')
class CaixaView(TemplateView):
    template_name = 'funcionarios/caixa.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mesas'] = Mesa.objects.all()
        return context


# ---------- Mixin para verificar grupo ----------
class GrupoRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    grupo = None  # Substituir pelo grupo exigido na view

    def test_func(self):
        user = self.request.user
        return user.groups.filter(name=self.grupo).exists()

    def handle_no_permission(self):
        # Redireciona para admin se não tiver permissão
        return redirect('/admin/')

