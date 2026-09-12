"""Filtro de exibição de valores em reais, usado nos templates."""
from django import template

from ..valores import formatar_brl

register = template.Library()


@register.filter(name='brl')
def brl(valor):
    if valor is None:
        return '—'
    return formatar_brl(valor)
