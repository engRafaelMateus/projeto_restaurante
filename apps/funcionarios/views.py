from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.utils.safestring import mark_safe
import json

from .models import Mesa, Pedido



# -----------------------------
# Funções de grupo
# -----------------------------
def grupo_caixa(user):
    return user.groups.filter(name='GrupoCaixa').exists()


def grupo_garcon(user):
    return user.groups.filter(name='GrupoGarcom').exists()


# -----------------------------
# Normalizar itens do pedido
# -----------------------------
def normalize_itens(raw):
    itens = []
    if not raw:
        return itens
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except:
            return [{'nome': raw, 'qtd': 1, 'valor': 0, 'subtotal': 0}]
    if isinstance(raw, list):
        for entry in raw:
            nome = entry.get('item') or entry.get('nome') or ''
            qtd = int(entry.get('quantidade') or entry.get('qtd') or 1)
            valor = float(entry.get('valor') or 0)
            itens.append({'nome': nome, 'qtd': qtd, 'valor': valor, 'subtotal': round(qtd * valor, 2)})
    return itens


# -----------------------------
# Views de página
# -----------------------------
@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
@method_decorator(user_passes_test(grupo_caixa, login_url='/admin/'), name='dispatch')
class CaixaView(TemplateView):
    template_name = 'funcionarios/caixa.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mesas = Mesa.objects.order_by('numero')
        pedidos_abertos = Pedido.objects.filter(status='aberto').select_related('mesa')
        mapa = {}

        for pedido in pedidos_abertos:
            itens_norm = normalize_itens(pedido.itens)
            total = float(pedido.total or sum(i['subtotal'] for i in itens_norm))
            mapa[str(pedido.mesa.numero)] = {
                'pedido_id': pedido.id,
                'itens': itens_norm,
                'total': round(total, 2),
                'status': pedido.status
            }

        ctx['mesas'] = mesas
        ctx['pedidos_map_json'] = mark_safe(json.dumps(mapa))
        return ctx


@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
@method_decorator(user_passes_test(grupo_garcon, login_url='/admin/'), name='dispatch')
class ComandaView(TemplateView):
    template_name = 'funcionarios/comanda.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        mesas = Mesa.objects.order_by('numero').all()
        ctx['mesas'] = mesas
        return ctx
