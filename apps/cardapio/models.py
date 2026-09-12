"""
Catálogo do restaurante.

Modelagem deliberadamente genérica: um único modelo `Produto` atende lanche,
pizza, bebida, sobremesa e qualquer item futuro. A diferença entre eles é
dado (`Categoria`), não código — não existe uma classe Django por tipo de
produto. Ver docs/ARQUITETURA.md, seção "Catálogo".
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    validate_image_file_extension,
)
from django.db import models
from django.utils.text import slugify

TAMANHO_MAXIMO_IMAGEM = 2 * 1024 * 1024  # 2 MB


def validar_tamanho_da_imagem(arquivo):
    """Recusa imagens grandes demais antes de gravá-las em disco."""
    if arquivo.size > TAMANHO_MAXIMO_IMAGEM:
        raise ValidationError(
            'Imagem muito grande (%(atual)s MB). O limite é %(limite)s MB.',
            params={
                'atual': round(arquivo.size / 1024 / 1024, 1),
                'limite': TAMANHO_MAXIMO_IMAGEM // 1024 // 1024,
            },
        )


class Registro(models.Model):
    """Campos de auditoria compartilhados por todo o catálogo.

    Classe abstrata: não vira tabela, apenas injeta colunas nas filhas.
    É o uso de herança que faz sentido aqui — comportamento comum de
    registro, e não uma hierarquia de tipos de produto.
    """

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)
    ativo = models.BooleanField(
        'Ativo',
        default=True,
        help_text='Desmarque para retirar do cadastro sem apagar o histórico de vendas.',
    )

    class Meta:
        abstract = True


class CategoriaQuerySet(models.QuerySet):
    def ativas(self):
        return self.filter(ativo=True)


class Categoria(Registro):
    nome = models.CharField('Nome', max_length=60, unique=True)
    slug = models.SlugField('Identificador', max_length=70, unique=True, blank=True)
    ordem = models.PositiveSmallIntegerField(
        'Ordem de exibição',
        default=100,
        help_text='Menor número aparece primeiro nas telas.',
    )

    objects = CategoriaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)[:70]
        super().save(*args, **kwargs)


class AdicionalQuerySet(models.QuerySet):
    def vendaveis(self):
        return self.filter(ativo=True, disponivel=True)


class Adicional(Registro):
    """Item cobrado junto de um produto: borda, gelo e limão, bacon extra.

    A ligação é por categoria: um adicional vale para todos os produtos das
    categorias associadas. Isso evita recadastrar o mesmo adicional em cada
    produto e mantém a validação simples no servidor.
    """

    nome = models.CharField('Nome', max_length=60)
    preco = models.DecimalField(
        'Preço',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    disponivel = models.BooleanField(
        'Disponível',
        default=True,
        help_text='Desmarque quando o adicional estiver temporariamente indisponível.',
    )
    categorias = models.ManyToManyField(
        Categoria,
        verbose_name='Categorias em que aparece',
        related_name='adicionais',
        blank=True,
    )

    objects = AdicionalQuerySet.as_manager()

    class Meta:
        verbose_name = 'Adicional'
        verbose_name_plural = 'Adicionais'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(fields=['nome'], name='adicional_nome_unico'),
            models.CheckConstraint(
                condition=models.Q(preco__gte=Decimal('0.00')),
                name='adicional_preco_nao_negativo',
            ),
        ]

    def __str__(self):
        return f'{self.nome} (+ R$ {self.preco})'

    @property
    def vendavel(self):
        return self.ativo and self.disponivel


class ProdutoQuerySet(models.QuerySet):
    def vendaveis(self):
        """Produtos que o servidor aceita lançar em uma comanda."""
        return self.filter(ativo=True, disponivel=True, categoria__ativo=True)

    def para_cardapio(self):
        return self.vendaveis().select_related('categoria').order_by(
            'categoria__ordem', 'categoria__nome', 'nome'
        )


class Produto(Registro):
    categoria = models.ForeignKey(
        Categoria,
        verbose_name='Categoria',
        on_delete=models.PROTECT,
        related_name='produtos',
    )
    nome = models.CharField('Nome', max_length=80)
    descricao = models.CharField('Descrição', max_length=300, blank=True)
    preco = models.DecimalField(
        'Preço',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    disponivel = models.BooleanField(
        'Disponível hoje',
        default=True,
        help_text='Desmarque quando o item acabar; o produto continua cadastrado.',
    )
    permite_meio_a_meio = models.BooleanField(
        'Permite meio a meio',
        default=False,
        help_text='Use em pizzas. A cobrança segue a regra definida em ATENDIMENTO_REGRA_MEIO_A_MEIO.',
    )
    imagem = models.ImageField(
        'Imagem',
        upload_to='produtos/',
        blank=True,
        validators=[validate_image_file_extension, validar_tamanho_da_imagem],
    )

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['categoria__ordem', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'nome'], name='produto_nome_unico_por_categoria'
            ),
            models.CheckConstraint(
                condition=models.Q(preco__gt=Decimal('0.00')),
                name='produto_preco_positivo',
            ),
        ]
        indexes = [
            models.Index(fields=['categoria', 'disponivel'], name='idx_produto_cat_disp'),
        ]

    def __str__(self):
        return self.nome

    @property
    def vendavel(self):
        return self.ativo and self.disponivel and self.categoria.ativo

    def adicionais_permitidos(self):
        """Adicionais que o servidor aceita neste produto."""
        return Adicional.objects.vendaveis().filter(categorias=self.categoria)
