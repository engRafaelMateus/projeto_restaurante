"""
Aritmética de dinheiro.

Regra única do projeto: todo valor monetário é `Decimal` com duas casas e
arredondamento ROUND_HALF_UP (metade para cima), que é o arredondamento
comercial usado no Brasil. `float` nunca entra em cálculo financeiro —
0.1 + 0.2 != 0.3 em ponto flutuante binário, e uma conta de restaurante não
pode fechar com um centavo de diferença.

O arredondamento acontece uma única vez por linha da comanda, no subtotal.
Somar subtotais já arredondados evita que o total dependa da ordem dos itens.
"""
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal('0.01')
ZERO = Decimal('0.00')


def dinheiro(valor) -> Decimal:
    """Normaliza qualquer entrada numérica para Decimal com 2 casas."""
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def somar(valores) -> Decimal:
    total = ZERO
    for valor in valores:
        total += dinheiro(valor)
    return dinheiro(total)


def formatar_brl(valor) -> str:
    """Formata para exibição em pt-BR: 1234.5 -> 'R$ 1.234,50'."""
    valor = dinheiro(valor)
    inteiro, _, centavos = f'{valor:.2f}'.partition('.')
    negativo = inteiro.startswith('-')
    inteiro = inteiro.lstrip('-')
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return f'{"-" if negativo else ""}R$ {".".join(grupos)},{centavos}'
