"""
Validação das entradas que chegam pelo navegador.

O navegador manda **identificadores, quantidades e escolhas**. Nunca preço,
nunca total. Tudo que tem valor financeiro é buscado no catálogo pelo servidor.
Estes formulários são a fronteira onde o JSON vira objeto validado.
"""
from django import forms
from django.conf import settings

from apps.cardapio.models import Adicional, Produto

from .models import Pagamento


class ItemEnviadoForm(forms.Form):
    """Um item do envio do garçom.

    Repare no que **não** existe aqui: campo de preço. Se o navegador mandar
    `preco`, o campo é simplesmente ignorado — não há por onde ele entrar.
    """

    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        error_messages={
            'required': 'Item sem produto.',
            'invalid_choice': 'Produto inexistente, inativo ou indisponível.',
        },
    )
    produto_secundario = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        required=False,
        error_messages={
            'invalid_choice': 'Segundo sabor inexistente, inativo ou indisponível.'
        },
    )
    quantidade = forms.IntegerField(
        min_value=1,
        error_messages={
            'required': 'Informe a quantidade.',
            'invalid': 'Quantidade precisa ser um número inteiro.',
            'min_value': 'Quantidade precisa ser um inteiro maior que zero.',
        },
    )
    observacao = forms.CharField(max_length=140, required=False, strip=True)
    adicionais = forms.ModelMultipleChoiceField(
        queryset=Adicional.objects.none(),
        required=False,
        error_messages={'invalid_choice': 'Adicional inexistente ou indisponível.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Os querysets são montados aqui, e não na definição da classe, para
        # refletirem a disponibilidade **no momento do envio**.
        vendaveis = Produto.objects.vendaveis()
        self.fields['produto'].queryset = vendaveis
        self.fields['produto_secundario'].queryset = vendaveis
        self.fields['adicionais'].queryset = Adicional.objects.vendaveis()

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        maximo = settings.ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM
        if quantidade > maximo:
            raise forms.ValidationError(
                f'Quantidade máxima por item é {maximo}. Lance em linhas separadas.'
            )
        return quantidade

    def clean(self):
        dados = super().clean()
        produto = dados.get('produto')
        secundario = dados.get('produto_secundario')
        adicionais = dados.get('adicionais')

        if produto and secundario:
            if not produto.permite_meio_a_meio or not secundario.permite_meio_a_meio:
                raise forms.ValidationError(
                    'Este produto não aceita meio a meio.'
                )
            if produto.categoria_id != secundario.categoria_id:
                raise forms.ValidationError(
                    'Os dois sabores precisam ser da mesma categoria.'
                )
            if produto.pk == secundario.pk:
                # Dois sabores iguais é um sabor inteiro: normalizamos.
                dados['produto_secundario'] = None

        if produto and adicionais:
            permitidos = set(
                produto.adicionais_permitidos().values_list('id', flat=True)
            )
            invalidos = [a.nome for a in adicionais if a.pk not in permitidos]
            if invalidos:
                raise forms.ValidationError(
                    'Adicional não permitido para este produto: '
                    + ', '.join(sorted(invalidos))
                )
        return dados


class PagamentoForm(forms.Form):
    """Registro manual de pagamento. O valor da conta vem do servidor."""

    meio = forms.ChoiceField(
        choices=Pagamento.Meio.choices,
        error_messages={
            'required': 'Escolha o meio de pagamento.',
            'invalid_choice': 'Meio de pagamento inválido.',
        },
    )
    valor_recebido = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0
    )
    observacao = forms.CharField(max_length=200, required=False, strip=True)

    def __init__(self, *args, total_devido=None, **kwargs):
        self.total_devido = total_devido
        super().__init__(*args, **kwargs)

    def clean(self):
        dados = super().clean()
        meio = dados.get('meio')
        recebido = dados.get('valor_recebido')

        if meio == Pagamento.Meio.DINHEIRO:
            if recebido is None:
                raise forms.ValidationError(
                    'Em dinheiro, informe o valor recebido do cliente.'
                )
            if self.total_devido is not None and recebido < self.total_devido:
                raise forms.ValidationError(
                    'Valor recebido é menor que o total da conta.'
                )
        elif recebido is not None:
            # Valor recebido só faz sentido em dinheiro; nos demais meios a
            # conta é liquidada integralmente pelo total.
            dados['valor_recebido'] = None
        return dados


class CancelamentoItemForm(forms.Form):
    motivo = forms.CharField(
        max_length=200,
        strip=True,
        error_messages={'required': 'Informe o motivo do cancelamento.'},
    )

    def clean_motivo(self):
        motivo = self.cleaned_data['motivo'].strip()
        if len(motivo) < 3:
            raise forms.ValidationError('Descreva o motivo com pelo menos 3 caracteres.')
        return motivo
