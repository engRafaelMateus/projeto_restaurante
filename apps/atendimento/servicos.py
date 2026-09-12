"""
Operações de negócio do salão.

Este módulo é o único lugar que **escreve** comanda, item e pagamento.
As views cuidam de HTTP e permissão; aqui ficam as regras e as transações.
Assim a mesma regra vale para a API, para o admin e para os testes.

Garantias implementadas aqui:

* preço é sempre lido do catálogo no servidor;
* envio repetido não duplica item (idempotência por `Envio.referencia`);
* pagamento e encerramento acontecem na mesma transação;
* comanda encerrada não recebe item nem segundo pagamento.
"""
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cardapio.models import Produto

from .excecoes import ConflitoDeEstado, DadosInvalidos, NaoEncontrado
from .formularios import CancelamentoItemForm, ItemEnviadoForm, PagamentoForm
from .models import Comanda, Envio, ItemComanda, Mesa, Pagamento
from .valores import ZERO, dinheiro

logger = logging.getLogger('atendimento')

LIMITE_DE_ITENS_POR_ENVIO = 60


# ---------------------------------------------------------------------------
# Preço
# ---------------------------------------------------------------------------
def preco_do_item(produto: Produto, produto_secundario: Produto | None) -> Decimal:
    """Preço unitário praticado, calculado só com dados do catálogo.

    Meio a meio segue `settings.ATENDIMENTO_REGRA_MEIO_A_MEIO`:

    * 'maior' (padrão): cobra o sabor mais caro. É a regra combinada com o
      proprietário e a mais comum no mercado brasileiro — impede que um sabor
      caro seja diluído metade a metade com um barato.
    * 'media': média aritmética dos dois sabores.
    """
    if produto_secundario is None:
        return dinheiro(produto.preco)

    a, b = dinheiro(produto.preco), dinheiro(produto_secundario.preco)
    regra = getattr(settings, 'ATENDIMENTO_REGRA_MEIO_A_MEIO', 'maior')
    if regra == 'media':
        return dinheiro((a + b) / 2)
    return max(a, b)


def descricao_do_item(produto: Produto, produto_secundario: Produto | None) -> str:
    if produto_secundario is None:
        return produto.nome
    return f'Meio a meio: {produto.nome} / {produto_secundario.nome}'


# ---------------------------------------------------------------------------
# Comanda
# ---------------------------------------------------------------------------
@transaction.atomic
def abrir_ou_recuperar_comanda(numero_da_mesa: int, usuario) -> tuple[Comanda, bool]:
    """Devolve a comanda aberta da mesa, criando-a se ainda não existir.

    Abrir a mesma mesa duas vezes — inclusive em duas requisições simultâneas
    — sempre resulta em **uma** comanda: quem perde a corrida recebe
    IntegrityError da constraint `unica_comanda_aberta_por_mesa` e relê a
    comanda que o outro criou.
    """
    try:
        mesa = Mesa.objects.get(numero=numero_da_mesa, ativa=True)
    except Mesa.DoesNotExist:
        raise NaoEncontrado(f'Mesa {numero_da_mesa} não existe ou está inativa.') from None

    comanda = mesa.comandas.filter(status=Comanda.Status.ABERTA).first()
    if comanda:
        return comanda, False

    try:
        with transaction.atomic():
            comanda = Comanda.objects.create(mesa=mesa, aberta_por=usuario)
        return comanda, True
    except IntegrityError as erro:
        comanda = mesa.comandas.filter(status=Comanda.Status.ABERTA).first()
        if comanda is None:
            raise ConflitoDeEstado(
                'Não foi possível abrir a comanda desta mesa. Consulte o estado e tente de novo.'
            ) from erro
        return comanda, False


def _comanda_aberta_para_escrita(comanda_id: int) -> Comanda:
    """Carrega a comanda travando a linha, e recusa se não estiver aberta."""
    try:
        comanda = Comanda.objects.select_for_update().select_related('mesa').get(pk=comanda_id)
    except Comanda.DoesNotExist:
        raise NaoEncontrado('Comanda não encontrada.') from None
    if not comanda.esta_aberta:
        raise ConflitoDeEstado(
            f'Comanda #{comanda.pk} está {comanda.get_status_display().lower()} '
            'e não aceita alterações.',
            codigo='comanda_encerrada',
        )
    return comanda


# ---------------------------------------------------------------------------
# Envio de itens
# ---------------------------------------------------------------------------
def _validar_itens(itens_recebidos):
    """Valida a lista inteira antes de gravar qualquer linha.

    Ou tudo é válido, ou nada é gravado — nunca meio pedido no banco.
    """
    if not isinstance(itens_recebidos, list) or not itens_recebidos:
        raise DadosInvalidos('Envie ao menos um item.')
    if len(itens_recebidos) > LIMITE_DE_ITENS_POR_ENVIO:
        raise DadosInvalidos(
            f'Envio com itens demais (máximo {LIMITE_DE_ITENS_POR_ENVIO}).'
        )

    validados, erros = [], []
    for posicao, bruto in enumerate(itens_recebidos, start=1):
        if not isinstance(bruto, dict):
            erros.append(f'Item {posicao}: formato inválido.')
            continue
        formulario = ItemEnviadoForm(
            {
                'produto': bruto.get('produto_id'),
                'produto_secundario': bruto.get('produto_secundario_id') or None,
                'quantidade': bruto.get('quantidade'),
                'observacao': (bruto.get('observacao') or '')[:140],
                'adicionais': bruto.get('adicionais') or [],
            }
        )
        if formulario.is_valid():
            validados.append(formulario.cleaned_data)
        else:
            for mensagens in formulario.errors.values():
                erros.extend(f'Item {posicao}: {mensagem}' for mensagem in mensagens)

    if erros:
        raise DadosInvalidos(
            'O pedido não foi gravado porque há itens inválidos.',
            detalhes={'itens': erros},
        )
    return validados


@transaction.atomic
def enviar_itens(comanda_id: int, referencia_envio, itens_recebidos, usuario) -> dict:
    """Grava um lote de itens na comanda, de forma idempotente.

    `referencia_envio` é um UUID gerado pelo navegador **antes** do POST.
    Reenviar a mesma referência devolve o resultado do envio original e não
    grava nada — é o que protege contra clique duplo e contra a rede que cai
    depois que o servidor já gravou.
    """
    try:
        referencia = uuid.UUID(str(referencia_envio))
    except (ValueError, AttributeError, TypeError):
        raise DadosInvalidos('Referência de envio inválida.') from None

    # Envio já processado? Devolve o mesmo resultado, sem duplicar.
    existente = Envio.objects.filter(referencia=referencia).select_related('comanda').first()
    if existente is not None:
        if existente.comanda_id != comanda_id:
            raise DadosInvalidos('Esta referência de envio pertence a outra comanda.')
        return {
            'duplicado': True,
            'envio_id': existente.pk,
            'itens_gravados': existente.itens.count(),
            'comanda': existente.comanda.resumo_json(),
        }

    comanda = _comanda_aberta_para_escrita(comanda_id)
    itens_validados = _validar_itens(itens_recebidos)

    try:
        envio = Envio.objects.create(
            comanda=comanda, referencia=referencia, criado_por=usuario
        )
    except IntegrityError:
        # Duas requisições idênticas em paralelo: a segunda cai aqui.
        existente = Envio.objects.get(referencia=referencia)
        return {
            'duplicado': True,
            'envio_id': existente.pk,
            'itens_gravados': existente.itens.count(),
            'comanda': existente.comanda.resumo_json(),
        }

    itens = []
    for dados in itens_validados:
        produto = dados['produto']
        secundario = dados.get('produto_secundario')
        adicionais = list(dados.get('adicionais') or [])

        preco_unitario = preco_do_item(produto, secundario)
        preco_adicionais = ZERO
        detalhe_adicionais = []
        for adicional in adicionais:
            preco_adicionais += dinheiro(adicional.preco)
            detalhe_adicionais.append(
                {
                    'id': adicional.pk,
                    'nome': adicional.nome,
                    'preco': str(dinheiro(adicional.preco)),
                }
            )

        itens.append(
            ItemComanda(
                comanda=comanda,
                envio=envio,
                produto=produto,
                produto_secundario=secundario,
                descricao=descricao_do_item(produto, secundario)[:180],
                preco_unitario=preco_unitario,
                preco_adicionais=dinheiro(preco_adicionais),
                adicionais_detalhe=detalhe_adicionais,
                quantidade=dados['quantidade'],
                observacao=dados.get('observacao', ''),
                criado_por=usuario,
            )
        )

    ItemComanda.objects.bulk_create(itens)
    logger.info(
        'envio gravado comanda=%s envio=%s itens=%s usuario=%s',
        comanda.pk,
        envio.pk,
        len(itens),
        usuario.pk,
    )
    comanda.refresh_from_db()
    return {
        'duplicado': False,
        'envio_id': envio.pk,
        'itens_gravados': len(itens),
        'comanda': comanda.resumo_json(),
    }


# ---------------------------------------------------------------------------
# Cancelamento de item
# ---------------------------------------------------------------------------
@transaction.atomic
def cancelar_item(item_id: int, motivo: str, usuario) -> ItemComanda:
    formulario = CancelamentoItemForm({'motivo': motivo})
    if not formulario.is_valid():
        raise DadosInvalidos(
            ' '.join(m for lista in formulario.errors.values() for m in lista)
        )

    try:
        item = (
            ItemComanda.objects.select_for_update()
            .select_related('comanda')
            .get(pk=item_id)
        )
    except ItemComanda.DoesNotExist:
        raise NaoEncontrado('Item não encontrado.') from None

    if item.cancelado:
        raise ConflitoDeEstado('Este item já está cancelado.')
    if not item.comanda.esta_aberta:
        raise ConflitoDeEstado(
            'A comanda já foi encerrada; não é possível cancelar itens dela.'
        )

    item.cancelado_em = timezone.now()
    item.cancelado_por = usuario
    item.motivo_cancelamento = formulario.cleaned_data['motivo']
    item.save(update_fields=['cancelado_em', 'cancelado_por', 'motivo_cancelamento'])
    logger.info(
        'item cancelado item=%s comanda=%s usuario=%s', item.pk, item.comanda_id, usuario.pk
    )
    return item


# ---------------------------------------------------------------------------
# Pagamento e encerramento
# ---------------------------------------------------------------------------
@transaction.atomic
def registrar_pagamento(comanda_id: int, dados_recebidos: dict, usuario) -> Pagamento:
    """Liquida a comanda integralmente e a encerra, em uma só transação.

    O valor cobrado é **sempre** recalculado a partir dos itens gravados.
    Nada do que o navegador mandar como total é considerado.
    """
    comanda = _comanda_aberta_para_escrita(comanda_id)

    if Pagamento.objects.filter(comanda=comanda).exists():
        raise ConflitoDeEstado(
            'Esta comanda já tem pagamento registrado.', codigo='pagamento_duplicado'
        )

    total = comanda.total()
    if total <= ZERO:
        raise ConflitoDeEstado(
            'Comanda sem consumo. Use o cancelamento de comanda vazia para liberar a mesa.',
            codigo='comanda_sem_consumo',
        )

    formulario = PagamentoForm(dados_recebidos, total_devido=total)
    if not formulario.is_valid():
        raise DadosInvalidos(
            ' '.join(m for lista in formulario.errors.values() for m in lista)
        )

    meio = formulario.cleaned_data['meio']
    recebido = formulario.cleaned_data.get('valor_recebido')
    troco = None
    if meio == Pagamento.Meio.DINHEIRO:
        recebido = dinheiro(recebido)
        troco = dinheiro(recebido - total)
    else:
        recebido = None

    try:
        pagamento = Pagamento.objects.create(
            comanda=comanda,
            valor=total,
            meio=meio,
            valor_recebido=recebido,
            troco=troco,
            registrado_por=usuario,
            observacao=formulario.cleaned_data.get('observacao', ''),
        )
    except IntegrityError as erro:
        # OneToOne: outra requisição registrou o pagamento primeiro.
        raise ConflitoDeEstado(
            'Esta comanda já tem pagamento registrado.', codigo='pagamento_duplicado'
        ) from erro

    comanda.status = Comanda.Status.PAGA
    comanda.encerrada_em = timezone.now()
    comanda.encerrada_por = usuario
    comanda.save(update_fields=['status', 'encerrada_em', 'encerrada_por'])

    logger.info(
        'pagamento registrado comanda=%s valor=%s meio=%s usuario=%s',
        comanda.pk,
        total,
        meio,
        usuario.pk,
    )
    return pagamento


@transaction.atomic
def cancelar_comanda_vazia(comanda_id: int, motivo: str, usuario) -> Comanda:
    """Libera a mesa sem registrar venda. Só vale para comanda sem consumo."""
    comanda = _comanda_aberta_para_escrita(comanda_id)

    if comanda.itens_ativos.exists():
        raise ConflitoDeEstado(
            'A comanda tem itens lançados. Cancele os itens antes, ou registre o pagamento.',
            codigo='comanda_com_itens',
        )

    motivo = (motivo or '').strip()
    if len(motivo) < 3:
        raise DadosInvalidos('Informe o motivo do cancelamento da comanda.')

    comanda.status = Comanda.Status.CANCELADA
    comanda.encerrada_em = timezone.now()
    comanda.encerrada_por = usuario
    comanda.motivo_cancelamento = motivo[:200]
    comanda.save(
        update_fields=['status', 'encerrada_em', 'encerrada_por', 'motivo_cancelamento']
    )
    logger.info('comanda cancelada comanda=%s usuario=%s', comanda.pk, usuario.pk)
    return comanda
