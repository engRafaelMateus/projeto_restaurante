from . import perfis


def perfil_do_usuario(request):
    """Disponibiliza o perfil e as permissões de tela nos templates."""
    usuario = getattr(request, 'user', None)
    if usuario is None or not usuario.is_authenticated:
        return {'perfil_atual': None, 'pode': {}}

    return {
        'perfil_atual': perfis.perfil_do_usuario(usuario),
        'pode': {
            'lancar_itens': usuario.has_perm(perfis.LANCAR_ITENS),
            'cancelar_item': usuario.has_perm(perfis.CANCELAR_ITEM),
            'registrar_pagamento': usuario.has_perm(perfis.REGISTRAR_PAGAMENTO),
            'ver_historico': usuario.has_perm(perfis.VER_HISTORICO_FINANCEIRO),
        },
    }
