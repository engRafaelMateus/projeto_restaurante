"""Telas de operação: garçom, caixa e histórico."""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView, View

from . import perfis
from .models import Comanda, Mesa, Pagamento


class AposLoginView(LoginRequiredMixin, View):
    """Manda cada perfil para a sua tela logo após o login."""

    def get(self, request):
        usuario = request.user
        if usuario.has_perm(perfis.REGISTRAR_PAGAMENTO):
            return redirect('atendimento:caixa')
        if usuario.has_perm(perfis.LANCAR_ITENS):
            return redirect('atendimento:comanda')
        if usuario.is_staff:
            return redirect('admin:index')
        return redirect('clientes:index')


class ComandaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Tela do garçom, desenhada para celular."""

    template_name = 'atendimento/comanda.html'
    permission_required = perfis.LANCAR_ITENS
    # Visitante é levado ao login; usuário autenticado sem permissão recebe 403
    # (comportamento padrão do AccessMixin), e não um redirecionamento em laço.

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['tela_atual'] = 'comanda'
        contexto['mesas'] = Mesa.objects.filter(ativa=True)
        contexto['quantidade_maxima'] = settings.ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM
        return contexto


class CaixaView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Painel do caixa, desenhado para desktop."""

    template_name = 'atendimento/caixa.html'
    permission_required = 'atendimento.view_comanda'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['tela_atual'] = 'caixa'
        contexto['mesas'] = Mesa.objects.filter(ativa=True)
        contexto['meios_de_pagamento'] = Pagamento.Meio.choices
        return contexto


class HistoricoView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Comandas encerradas, com filtros de período, mesa e situação."""

    template_name = 'atendimento/historico.html'
    permission_required = perfis.VER_HISTORICO_FINANCEIRO

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        parametros = self.request.GET

        comandas = (
            Comanda.objects.encerradas()
            .select_related('mesa', 'aberta_por', 'encerrada_por', 'pagamento')
            .prefetch_related('itens')
            .order_by('-encerrada_em')
        )

        de = parametros.get('de') or ''
        ate = parametros.get('ate') or ''
        mesa = parametros.get('mesa') or ''
        situacao = parametros.get('situacao') or ''

        if de:
            comandas = comandas.filter(encerrada_em__date__gte=de)
        if ate:
            comandas = comandas.filter(encerrada_em__date__lte=ate)
        if mesa.isdigit():
            comandas = comandas.filter(mesa__numero=int(mesa))
        if situacao in (Comanda.Status.PAGA, Comanda.Status.CANCELADA):
            comandas = comandas.filter(status=situacao)

        comandas = list(comandas[:200])

        # Total recebido vem do registro de pagamento, nunca de comanda aberta.
        pagamentos = [c.pagamento for c in comandas if hasattr(c, 'pagamento')]
        total_recebido = sum((p.valor for p in pagamentos), start=0)

        contexto.update(
            {
                'tela_atual': 'historico',
                'comandas': comandas,
                'filtros': {'de': de, 'ate': ate, 'mesa': mesa, 'situacao': situacao},
                'situacoes': [
                    (Comanda.Status.PAGA, 'Paga'),
                    (Comanda.Status.CANCELADA, 'Cancelada'),
                ],
                'total_recebido': total_recebido,
                'quantidade_paga': len(pagamentos),
                'hoje': timezone.localdate().isoformat(),
            }
        )
        return contexto
