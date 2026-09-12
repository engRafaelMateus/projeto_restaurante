from django.views.generic import TemplateView

from .models import Adicional, Categoria, Produto


class CardapioPublicoView(TemplateView):
    """Cardápio de consulta, aberto ao público.

    Somente leitura: nesta versão o pedido é feito no salão, pelo garçom.
    Não há sacola nem checkout — ver "Limitações conhecidas" no README.
    """

    template_name = 'cardapio/publico.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        produtos = Produto.objects.para_cardapio()
        categorias = (
            Categoria.objects.ativas()
            .filter(produtos__in=produtos)
            .distinct()
            .order_by('ordem', 'nome')
        )
        por_categoria = {categoria.id: [] for categoria in categorias}
        for produto in produtos:
            por_categoria.setdefault(produto.categoria_id, []).append(produto)

        contexto['secoes'] = [
            {
                'categoria': categoria,
                'produtos': por_categoria.get(categoria.id, []),
                'adicionais': [
                    adicional
                    for adicional in Adicional.objects.vendaveis().filter(
                        categorias=categoria
                    )
                ],
            }
            for categoria in categorias
        ]
        return contexto
