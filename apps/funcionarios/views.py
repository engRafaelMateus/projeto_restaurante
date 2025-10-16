from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Mesa, Pedido
from apps.pedidos.models import Categoria, Pizza, Sobremesa, Cerveja, Refrigerante, Extra, Borda


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


# -----------------------------
# API - Abrir mesa / criar pedido
# -----------------------------
@login_required
@user_passes_test(grupo_garcon)
@require_POST
def abrir_mesa(request):
    data = json.loads(request.body)
    numero_mesa = data.get("mesa")
    if not numero_mesa:
        return JsonResponse({"error": "Mesa não informada"}, status=400)

    mesa, _ = Mesa.objects.get_or_create(numero=numero_mesa)
    pedido, created = Pedido.objects.get_or_create(
        mesa=mesa, status="aberto", defaults={"itens": []}
    )

    return JsonResponse({
        "pedido_id": pedido.id,
        "mesa": mesa.numero,
        "itens": pedido.itens or [],
        "total": float(pedido.total or 0)
    })


# -----------------------------
# API - Listar categorias
# -----------------------------
@login_required
@user_passes_test(grupo_garcon)
def listar_categorias(request):
    categorias = Categoria.objects.filter(ativo=True)
    data = [{"id": c.id, "nome": c.nome} for c in categorias]
    return JsonResponse({"categorias": data})


# -----------------------------
# API - Listar itens por categoria
# -----------------------------
@login_required
@user_passes_test(grupo_garcon)
def listar_itens(request, categoria_id):
    itens = []

    # Pizzas
    for p in Pizza.objects.filter(categoria_id=categoria_id, ativo=True):
        itens.append({"id": p.id, "nome": p.nome, "valor": float(p.valor)})

    # Sobremesas
    for s in Sobremesa.objects.filter(categoria_id=categoria_id, ativo=True):
        itens.append({"id": s.id, "nome": s.nome, "valor": float(s.valor)})

    # Extras
    for e in Extra.objects.filter(categorias__id=categoria_id, ativo=True):
        itens.append({"id": e.id, "nome": e.nome, "valor": float(e.valor)})

    # Refrigerantes
    for r in Refrigerante.objects.filter(categoria_id=categoria_id, ativo=True):
        itens.append({"id": r.id, "nome": r.nome, "valor": float(r.valor)})

    # Cervejas
    for c in Cerveja.objects.filter(categoria_id=categoria_id, ativo=True):
        itens.append({"id": c.id, "nome": c.nome, "valor": float(c.valor)})

    # Bordas (opcional)
    for b in Borda.objects.filter(ativo=True):
        itens.append({"id": b.id, "nome": b.nome, "valor": float(b.valor)})

    return JsonResponse(itens, safe=False)


# -----------------------------
# API - Adicionar item ao pedido
# -----------------------------
@login_required
@user_passes_test(grupo_garcon)
@require_POST
def adicionar_item(request):
    data = json.loads(request.body)
    mesa_num = data.get("mesa")
    item = data.get("item")
    if not mesa_num or not item:
        return JsonResponse({"error": "Mesa ou item não informado"}, status=400)
    try:
        mesa = Mesa.objects.get(numero=mesa_num)
        pedido = Pedido.objects.get(mesa=mesa, status="aberto")
    except (Mesa.DoesNotExist, Pedido.DoesNotExist):
        return JsonResponse({"error": "Mesa ou pedido não encontrado"}, status=404)

    itens = pedido.itens or []
    itens.append(item)
    pedido.itens = itens
    pedido.total = sum(i.get("qtd", 1) * i.get("valor", 0) for i in itens)
    pedido.save()
    return JsonResponse({"ok": True, "itens": itens, "total": float(pedido.total)})


# -----------------------------
# API - Enviar pedido final
# -----------------------------
@csrf_exempt
def enviar_pedido(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método inválido"})

    try:
        data = json.loads(request.body)
        mesa_num = data.get("mesa")
        itens = data.get("itens", [])

        if not mesa_num or not itens:
            return JsonResponse({"ok": False, "erro": "Dados incompletos"})

        mesa, _ = Mesa.objects.get_or_create(numero=mesa_num)
        total = sum([float(i["valor"]) * int(i.get("qtd", 1)) for i in itens])

        pedido = Pedido.objects.create(
            mesa=mesa,
            itens=itens,
            total=total,
            status='aberto'
        )

        return JsonResponse({"ok": True, "pedido_id": pedido.id})

    except Exception as e:
        return JsonResponse({"ok": False, "erro": str(e)})


# -----------------------------
# API - Fechar pedido (Caixa)
# -----------------------------
@login_required(login_url='/admin/login/')
@user_passes_test(grupo_caixa, login_url='/admin/')
@require_POST
def fechar_pedido(request, pk):
    try:
        pedido = Pedido.objects.get(pk=pk)
    except Pedido.DoesNotExist:
        return JsonResponse({'error': 'Pedido não encontrado'}, status=404)

    pedido.status = 'fechado'
    pedido.save()
    return JsonResponse({'ok': True})
