from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Pedido, Mesa
from apps.pedidos.models import (Categoria, Pizza,
                                 Sobremesa, Cerveja,
                                 Refrigerante, Extra,
                                 Borda)
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps


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


# -----------------------------
# API - Listar categorias
# -----------------------------
@login_required
@user_passes_test(grupo_garcon)
def listar_categorias(request):
    categorias = Categoria.objects.filter(ativo=True)
    data = [{"id": c.id, "nome": c.nome} for c in categorias]
    return JsonResponse({"categorias": data})


# Listar itens de uma categoria
@login_required
@user_passes_test(grupo_garcon)
def listar_itens(request, categoria_id):
    categoria = Categoria.objects.get(pk=categoria_id)
    itens = []
    subcategorias = []

    # Encontra automaticamente QUAL modelo principal usa essa categoria
    modelos = apps.get_models(include_auto_created=False)
    modelo_principal = None

    for m in modelos:
        # Pula modelos que não têm categoria
        if not hasattr(m, 'categoria_id'):
            continue

        if m._meta.app_label == 'pedidos' and m.objects.filter(categoria_id=categoria_id, ativo=True).exists():
            modelo_principal = m
            break

    # Carrega os itens da categoria
    if modelo_principal:
        for obj in modelo_principal.objects.filter(categoria_id=categoria_id, ativo=True):
            itens.append({
                "id": obj.id,
                "nome": obj.nome,
                "valor": float(getattr(obj, 'valor', 0))
            })

        # Agora procura dentro do modelo principal por todos os campos que são ManyToMany
        # (ou seja, possíveis subcategorias)
        for field in modelo_principal._meta.get_fields():
            if field.many_to_many and not field.auto_created:
                related_model = field.related_model
                qs = related_model.objects.filter(ativo=True)

                if qs.exists():
                    subcategorias.append({
                        "tipo": related_model.__name__,
                        "itens": [
                            {"id": o.id, "nome": o.nome, "valor": float(o.valor)} for o in qs
                        ]
                    })

    # Também adiciona automaticamente os "extras" que foram vinculados a essa categoria via ManyToMany
    extras_categoria = Extra.objects.filter(categorias=categoria, ativo=True)
    if extras_categoria.exists():
        subcategorias.append({
            "tipo": "Extra",
            "itens": [
                {"id": e.id, "nome": e.nome, "valor": float(e.valor)} for e in extras_categoria
            ]
        })

    return JsonResponse({"itens": itens, "subcategorias": subcategorias})


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

        # Verifica se já existe pedido aberto
        pedido, created = Pedido.objects.get_or_create(
            mesa=mesa,
            status='aberto',
            defaults={"itens": [], "total": 0}
        )

        # Adiciona os itens novos ao pedido existente
        itens_existentes = pedido.itens or []
        itens_existentes.extend(itens)
        pedido.itens = itens_existentes
        pedido.total = sum(i.get("qtd", 1) * float(i.get("valor", 0)) for i in itens_existentes)
        pedido.save()

        return JsonResponse({"ok": True, "pedido_id": pedido.id, "total": float(pedido.total)})

    except Exception as e:
        return JsonResponse({"ok": False, "erro": str(e)})


@login_required
@user_passes_test(grupo_garcon)
def pedido_aberto(request, mesa_num):
    try:
        mesa = Mesa.objects.get(numero=mesa_num)
        pedido = Pedido.objects.get(mesa=mesa, status='aberto')
        return JsonResponse({
            "pedido_id": pedido.id,
            "itens": pedido.itens or [],
            "total": float(pedido.total or 0)
        })
    except (Mesa.DoesNotExist, Pedido.DoesNotExist):
        return JsonResponse({
            "pedido_id": None,
            "itens": [],
            "total": 0
        })
