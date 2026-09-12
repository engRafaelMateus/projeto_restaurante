"""
Perfis de acesso.

Não existe modelo próprio de funcionário nem campo de senha nosso: quem
autentica é `django.contrib.auth.User`, e o perfil é o **grupo** do Django.
A senha é sempre hash do Django (PBKDF2), nunca texto.

A interface pode esconder botões, mas a autorização real está no servidor:
cada endpoint exige a permissão correspondente desta tabela.
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

GARCOM = 'Garçom'
CAIXA = 'Caixa'
ADMINISTRACAO = 'Administração'

# Permissões customizadas declaradas em Comanda.Meta.permissions
LANCAR_ITENS = 'atendimento.lancar_itens'
CANCELAR_ITEM = 'atendimento.cancelar_item'
REGISTRAR_PAGAMENTO = 'atendimento.registrar_pagamento'
VER_HISTORICO_FINANCEIRO = 'atendimento.ver_historico_financeiro'

# codename -> app_label do modelo dono da permissão
_CONSULTA = [
    ('view_mesa', 'atendimento'),
    ('view_comanda', 'atendimento'),
    ('view_itemcomanda', 'atendimento'),
    ('view_produto', 'cardapio'),
    ('view_categoria', 'cardapio'),
    ('view_adicional', 'cardapio'),
]

PERMISSOES_POR_GRUPO = {
    GARCOM: _CONSULTA + [('lancar_itens', 'atendimento')],
    CAIXA: _CONSULTA
    + [
        ('lancar_itens', 'atendimento'),
        ('cancelar_item', 'atendimento'),
        ('registrar_pagamento', 'atendimento'),
        ('ver_historico_financeiro', 'atendimento'),
        ('view_pagamento', 'atendimento'),
    ],
    ADMINISTRACAO: _CONSULTA
    + [
        ('lancar_itens', 'atendimento'),
        ('cancelar_item', 'atendimento'),
        ('registrar_pagamento', 'atendimento'),
        ('ver_historico_financeiro', 'atendimento'),
        ('view_pagamento', 'atendimento'),
        ('add_produto', 'cardapio'),
        ('change_produto', 'cardapio'),
        ('delete_produto', 'cardapio'),
        ('add_categoria', 'cardapio'),
        ('change_categoria', 'cardapio'),
        ('delete_categoria', 'cardapio'),
        ('add_adicional', 'cardapio'),
        ('change_adicional', 'cardapio'),
        ('delete_adicional', 'cardapio'),
        ('add_mesa', 'atendimento'),
        ('change_mesa', 'atendimento'),
        ('add_user', 'auth'),
        ('change_user', 'auth'),
        ('view_user', 'auth'),
    ],
}


def sincronizar_grupos():
    """Cria/atualiza os três grupos com suas permissões. Pode rodar sempre."""
    resultado = {}
    for nome, permissoes in PERMISSOES_POR_GRUPO.items():
        grupo, _ = Group.objects.get_or_create(name=nome)
        objetos = []
        for codename, app_label in permissoes:
            tipos = ContentType.objects.filter(app_label=app_label)
            permissao = Permission.objects.filter(
                codename=codename, content_type__in=tipos
            ).first()
            if permissao:
                objetos.append(permissao)
        grupo.permissions.set(objetos)
        resultado[nome] = len(objetos)
    return resultado


def perfil_do_usuario(usuario):
    """Nome do perfil para exibir na interface. Não substitui a autorização."""
    if not usuario.is_authenticated:
        return None
    if usuario.is_superuser:
        return ADMINISTRACAO
    nomes = set(usuario.groups.values_list('name', flat=True))
    for perfil in (ADMINISTRACAO, CAIXA, GARCOM):
        if perfil in nomes:
            return perfil
    return None
