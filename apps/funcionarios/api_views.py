from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Pedido, Mesa
from apps.pedidos.models import Categoria, Pizza, Sobremesa, Cerveja, Refrigerante, Extra, Borda
import json
from django.views.decorators.csrf import csrf_exempt


def grupo_caixa(user):
    return user.groups.filter(name='GrupoCaixa').exists()


# Verifica grupo garçom
def grupo_garcon(user):
    return user.groups.filter(name='GrupoGarcom').exists()


# Abrir ou criar pedido da mesa
@login_required
@user_passes_test(grupo_garcon)
@require_POST
def abrir_mesa(request):
    data = json.loads(request.body)
    numero_mesa = data.get("mesa")
    if not numero_mesa:
        return JsonResponse({"error": "Mesa não informada"}, status=400)

    mesa, _ = Mesa.objects.get_or_create(numero=numero_mesa)
    pedido, created = Pedido.objects.get_or_create(mesa=mesa, status="aberto", defaults={"itens": []})

    return JsonResponse({
        "pedido_id": pedido.id,
        "mesa": mesa.numero,
        "itens": pedido.itens or [],
        "total": float(pedido.total or 0)
    })


# Listar categorias
@login_required
@user_passes_test(grupo_garcon)
def listar_categorias(request):
    categorias = Categoria.objects.filter(ativo=True).values("id", "nome")
    return JsonResponse({"categorias": list(categorias)})


# Listar itens de uma categoria
@login_required
@user_passes_test(grupo_garcon)
def listar_itens(request, categoria_id):
    try:
        categoria = Categoria.objects.get(pk=categoria_id)
    except Categoria.DoesNotExist:
        return JsonResponse({"error": "Categoria não encontrada"}, status=404)

    # Busca todos os itens da categoria
    itens = []

    # Pizzas
    pizzas = Pizza.objects.filter(categoria=categoria)
    for p in pizzas:
        itens.append({"id": p.id, "nome": p.nome, "preco": float(p.valor)})

    # Sobremesas
    sobremesas = Sobremesa.objects.filter(categoria=categoria)
    for s in sobremesas:
        itens.append({"id": s.id, "nome": s.nome, "preco": float(s.valor)})

    # Cervejas
    cervejas = Cerveja.objects.filter(categoria=categoria)
    for c in cervejas:
        itens.append({"id": c.id, "nome": c.nome, "preco": float(c.valor)})

    # Refrigerantes
    refrigerantes = Refrigerante.objects.filter(categoria=categoria)
    for r in refrigerantes:
        itens.append({"id": r.id, "nome": r.nome, "preco": float(r.valor)})

    return JsonResponse({"itens": itens})


# Adicionar item ao pedido
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

    # Atualiza itens
    itens = pedido.itens or []
    itens.append(item)
    pedido.itens = itens
    pedido.total = sum(i.get("qtd", 1) * i.get("preco", 0) for i in itens)
    pedido.save()
    return JsonResponse({"ok": True, "itens": itens, "total": float(pedido.total)})


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


# -----------------------------
# Lista categorias
# -----------------------------
def listar_categorias(request):
    categorias = Categoria.objects.filter(ativo=True)
    data = [{"id": c.id, "nome": c.nome} for c in categorias]
    return JsonResponse({"categorias": data})


# -----------------------------
# Lista itens por categoria
# -----------------------------
def listar_itens(request, categoria_id):
    itens = []

    # Pizzas
    pizzas = Pizza.objects.filter(categoria_id=categoria_id, ativo=True)
    for p in pizzas:
        itens.append({"id": p.id, "nome": p.nome, "valor": float(p.valor)})

    # Extras
    extras = Extra.objects.filter(categorias__id=categoria_id, ativo=True)
    for e in extras:
        itens.append({"id": e.id, "nome": e.nome, "valor": float(e.valor)})

    # Refrigerantes
    refrigerantes = Refrigerante.objects.filter(categoria_id=categoria_id, ativo=True)
    for r in refrigerantes:
        itens.append({"id": r.id, "nome": r.nome, "valor": float(r.valor)})

    # Cervejas
    cervejas = Cerveja.objects.filter(categoria_id=categoria_id, ativo=True)
    for c in cervejas:
        itens.append({"id": c.id, "nome": c.nome, "valor": float(c.valor)})

    # Sobremesas
    sobremesas = Sobremesa.objects.filter(categoria_id=categoria_id, ativo=True)
    for s in sobremesas:
        itens.append({"id": s.id, "nome": s.nome, "valor": float(s.valor)})

    # Bordas (opcional, se quiser incluir)
    bordas = Borda.objects.filter(ativo=True)
    for b in bordas:
        itens.append({"id": b.id, "nome": b.nome, "valor": float(b.valor)})

    return JsonResponse(itens, safe=False)


# -----------------------------
# Recebe e salva pedido
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
        total = sum([float(i["preco"]) for i in itens])

        pedido = Pedido.objects.create(
            mesa=mesa,
            itens=itens,
            total=total,
            status='aberto'
        )

        return JsonResponse({"ok": True, "pedido_id": pedido.id})

    except Exception as e:
        return JsonResponse({"ok": False, "erro": str(e)})
