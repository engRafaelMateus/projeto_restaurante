"""
Endpoints JSON usados pelas telas de garçom e caixa.

Regras que valem para todos eles:

* exigem sessão autenticada — visitante recebe 401 em JSON, não redirecionamento
  para uma página de login que o `fetch` não saberia tratar;
* exigem a permissão do perfil, verificada **no servidor**, mesmo que a
  interface já esconda o botão;
* mutações são POST e passam pelo CSRF do Django (nenhum `csrf_exempt`);
* erro previsto vira mensagem legível; erro inesperado vira 500 genérico e o
  stack trace fica no log do servidor, não na resposta.
"""
import functools
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.cardapio.models import Adicional, Categoria, Produto

from . import perfis, servicos
from .excecoes import ErroDeNegocio, NaoEncontrado
from .models import Comanda, Mesa
from .valores import formatar_brl, somar

logger = logging.getLogger('atendimento')

TAMANHO_MAXIMO_DO_CORPO = 256 * 1024  # 256 KB


def endpoint(permissao=None, metodos=('POST',), corpo_json=True):
    """Empacota autenticação, permissão, parsing e tratamento de erro."""

    def decorador(funcao):
        @require_http_methods(list(metodos))
        @functools.wraps(funcao)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'ok': False, 'codigo': 'nao_autenticado', 'erro': 'Faça login para continuar.'},
                    status=401,
                )
            if permissao and not request.user.has_perm(permissao):
                return JsonResponse(
                    {
                        'ok': False,
                        'codigo': 'sem_permissao',
                        'erro': 'Seu perfil não tem permissão para esta operação.',
                    },
                    status=403,
                )

            dados = {}
            if corpo_json and request.method in ('POST', 'PUT', 'PATCH'):
                if len(request.body) > TAMANHO_MAXIMO_DO_CORPO:
                    return JsonResponse(
                        {'ok': False, 'codigo': 'corpo_grande', 'erro': 'Requisição grande demais.'},
                        status=413,
                    )
                try:
                    dados = json.loads(request.body or b'{}')
                except (ValueError, UnicodeDecodeError):
                    return JsonResponse(
                        {'ok': False, 'codigo': 'json_invalido', 'erro': 'Requisição malformada.'},
                        status=400,
                    )
                if not isinstance(dados, dict):
                    return JsonResponse(
                        {'ok': False, 'codigo': 'json_invalido', 'erro': 'Requisição malformada.'},
                        status=400,
                    )

            try:
                return funcao(request, dados, *args, **kwargs)
            except ErroDeNegocio as erro:
                return JsonResponse(erro.como_dicionario(), status=erro.status_http)
            except Exception:
                logger.exception('falha inesperada em %s', funcao.__name__)
                return JsonResponse(
                    {
                        'ok': False,
                        'codigo': 'erro_interno',
                        'erro': 'Não foi possível concluir a operação. Consulte o estado da comanda antes de tentar de novo.',
                    },
                    status=500,
                )

        return wrapper

    return decorador


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------
@endpoint(permissao='atendimento.view_comanda', metodos=('GET',), corpo_json=False)
def catalogo(request, _dados):
    """Catálogo vendável, já agrupado por categoria, para a tela do garçom."""
    produtos = Produto.objects.para_cardapio()
    adicionais = Adicional.objects.vendaveis().prefetch_related('categorias')

    por_categoria = {}
    for produto in produtos:
        por_categoria.setdefault(produto.categoria_id, []).append(
            {
                'id': produto.pk,
                'nome': produto.nome,
                'descricao': produto.descricao,
                'preco': str(produto.preco),
                'preco_formatado': formatar_brl(produto.preco),
                'meio_a_meio': produto.permite_meio_a_meio,
            }
        )

    adicionais_por_categoria = {}
    for adicional in adicionais:
        for categoria in adicional.categorias.all():
            adicionais_por_categoria.setdefault(categoria.id, []).append(
                {
                    'id': adicional.pk,
                    'nome': adicional.nome,
                    'preco': str(adicional.preco),
                    'preco_formatado': formatar_brl(adicional.preco),
                }
            )

    categorias = [
        {
            'id': categoria.id,
            'nome': categoria.nome,
            'produtos': por_categoria.get(categoria.id, []),
            'adicionais': adicionais_por_categoria.get(categoria.id, []),
        }
        for categoria in Categoria.objects.ativas().order_by('ordem', 'nome')
        if por_categoria.get(categoria.id)
    ]
    return JsonResponse({'ok': True, 'categorias': categorias})


@endpoint(permissao='atendimento.view_comanda', metodos=('GET',), corpo_json=False)
def estado_do_salao(request, _dados):
    """Situação de todas as mesas. É o que o caixa consulta periodicamente."""
    comandas = (
        Comanda.objects.abertas()
        .select_related('mesa', 'aberta_por')
        .prefetch_related('itens')
    )
    abertas = {comanda.mesa_id: comanda for comanda in comandas}

    mesas = []
    for mesa in Mesa.objects.filter(ativa=True):
        comanda = abertas.get(mesa.pk)
        if comanda is None:
            mesas.append(
                {
                    'numero': mesa.numero,
                    'ocupada': False,
                    'comanda_id': None,
                    'total': '0.00',
                    'total_formatado': formatar_brl(0),
                    'itens': 0,
                    'aberta_por': None,
                }
            )
            continue

        # Usa os itens já trazidos pelo prefetch: uma consulta para todas as
        # comandas abertas, em vez de uma por mesa a cada polling.
        ativos = [item for item in comanda.itens.all() if item.cancelado_em is None]
        total = somar(item.subtotal for item in ativos)
        mesas.append(
            {
                'numero': mesa.numero,
                'ocupada': True,
                'comanda_id': comanda.pk,
                'total': str(total),
                'total_formatado': formatar_brl(total),
                'itens': len(ativos),
                'aberta_por': comanda.aberta_por.get_username()
                if comanda.aberta_por_id
                else None,
            }
        )
    return JsonResponse({'ok': True, 'mesas': mesas})


@endpoint(permissao='atendimento.view_comanda', metodos=('GET',), corpo_json=False)
def detalhe_da_comanda(request, _dados, comanda_id):
    comanda = (
        Comanda.objects.filter(pk=comanda_id)
        .select_related('mesa', 'aberta_por')
        .first()
    )
    if comanda is None:
        raise NaoEncontrado('Comanda não encontrada.')
    return JsonResponse({'ok': True, 'comanda': comanda.resumo_json()})


@endpoint(permissao='atendimento.view_comanda', metodos=('GET',), corpo_json=False)
def comanda_aberta_da_mesa(request, _dados, numero_da_mesa):
    """Usado pelo garçom ao abrir a mesa: devolve o que já está no servidor."""
    comanda = (
        Comanda.objects.abertas()
        .select_related('mesa')
        .filter(mesa__numero=numero_da_mesa)
        .first()
    )
    if comanda is None:
        return JsonResponse({'ok': True, 'comanda': None})
    return JsonResponse({'ok': True, 'comanda': comanda.resumo_json()})


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------
@endpoint(permissao=perfis.LANCAR_ITENS)
def abrir_comanda(request, dados):
    numero = dados.get('mesa')
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return JsonResponse(
            {'ok': False, 'codigo': 'dados_invalidos', 'erro': 'Informe o número da mesa.'},
            status=400,
        )

    comanda, criada = servicos.abrir_ou_recuperar_comanda(numero, request.user)
    return JsonResponse({'ok': True, 'criada': criada, 'comanda': comanda.resumo_json()})


@endpoint(permissao=perfis.LANCAR_ITENS)
def enviar_itens(request, dados, comanda_id):
    resultado = servicos.enviar_itens(
        comanda_id=comanda_id,
        referencia_envio=dados.get('referencia_envio'),
        itens_recebidos=dados.get('itens'),
        usuario=request.user,
    )
    return JsonResponse({'ok': True, **resultado})


@endpoint(permissao=perfis.CANCELAR_ITEM)
def cancelar_item(request, dados, item_id):
    item = servicos.cancelar_item(item_id, dados.get('motivo', ''), request.user)
    item.comanda.refresh_from_db()
    return JsonResponse({'ok': True, 'comanda': item.comanda.resumo_json()})


@endpoint(permissao=perfis.REGISTRAR_PAGAMENTO)
def registrar_pagamento(request, dados, comanda_id):
    pagamento = servicos.registrar_pagamento(comanda_id, dados, request.user)
    return JsonResponse(
        {
            'ok': True,
            'pagamento': {
                'id': pagamento.pk,
                'valor': str(pagamento.valor),
                'valor_formatado': formatar_brl(pagamento.valor),
                'meio': pagamento.meio,
                'meio_exibicao': pagamento.get_meio_display(),
                'valor_recebido': str(pagamento.valor_recebido)
                if pagamento.valor_recebido is not None
                else None,
                'troco': str(pagamento.troco) if pagamento.troco is not None else None,
                'troco_formatado': formatar_brl(pagamento.troco)
                if pagamento.troco is not None
                else None,
                'registrado_por': pagamento.registrado_por.get_username(),
            },
            'comanda': pagamento.comanda.resumo_json(),
        }
    )


@endpoint(permissao=perfis.REGISTRAR_PAGAMENTO)
def cancelar_comanda(request, dados, comanda_id):
    comanda = servicos.cancelar_comanda_vazia(comanda_id, dados.get('motivo', ''), request.user)
    return JsonResponse({'ok': True, 'comanda': comanda.resumo_json()})
