from django.db import models
from pictures.models import PictureField
import datetime


class Base(models.Model):
    criado = models.DateTimeField('Criação', auto_now_add=True)
    modificado = models.DateTimeField('Modificado', auto_now=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        abstract = True


class Categoria(Base):
    nome = models.CharField('Categoria', max_length=100)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'

    def __str__(self):
        return self.nome


class Extra(Base):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=300, blank=True)
    categorias = models.ManyToManyField(Categoria, verbose_name='Categorias', related_name='extras', blank=True)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)

    # Imagem do extra
    imagem_width = models.PositiveIntegerField(null=True, blank=True)
    imagem_height = models.PositiveIntegerField(null=True, blank=True)
    imagem = PictureField(
        'Imagem',
        upload_to='extras',
        width_field='imagem_width',
        height_field='imagem_height',
        blank=True
    )

    class Meta:
        verbose_name = 'Extra'
        verbose_name_plural = 'Extras'

    def __str__(self):
        return self.nome


# Borda de pizza
class Borda(Base):
    nome = models.CharField('Nome', max_length=100)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)

    class Meta:
        verbose_name = 'Borda'
        verbose_name_plural = 'Bordas'

    def __str__(self):
        return self.nome


class Pizza(Base):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=300)
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria', on_delete=models.CASCADE)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)
    extras = models.ManyToManyField(Extra, blank=True, related_name='pizzas')
    bordas = models.ManyToManyField(Borda, blank=True, related_name='bordas')

    imagem_width = models.PositiveIntegerField(null=True, blank=True)
    imagem_height = models.PositiveIntegerField(null=True, blank=True)
    imagem = PictureField(
        'Imagem',
        upload_to='pizzas',
        width_field='imagem_width',
        height_field='imagem_height',
    )

    class Meta:
        verbose_name = 'Pizza'
        verbose_name_plural = 'Pizzas'

    def __str__(self):
        return self.nome


class Refrigerante(Base):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=300)
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria', on_delete=models.CASCADE)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)

    imagem_width = models.PositiveIntegerField(null=True, blank=True)
    imagem_height = models.PositiveIntegerField(null=True, blank=True)
    imagem = PictureField(
        'Imagem',
        upload_to='refrigerantes',
        width_field='imagem_width',
        height_field='imagem_height',
    )

    class Meta:
        verbose_name = 'Refrigerante'
        verbose_name_plural = 'Refrigerantes'

    def __str__(self):
        return self.nome


class Cerveja(Base):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=300)
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria', on_delete=models.CASCADE)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)

    imagem_width = models.PositiveIntegerField(null=True, blank=True)
    imagem_height = models.PositiveIntegerField(null=True, blank=True)
    imagem = PictureField(
        'Imagem',
        upload_to='cervejas',
        width_field='imagem_width',
        height_field='imagem_height',
    )

    class Meta:
        verbose_name = 'Cerveja'
        verbose_name_plural = 'Cervejas'

    def __str__(self):
        return self.nome


class Sobremesa(Base):
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=300)
    categoria = models.ForeignKey(Categoria, verbose_name='Categoria', on_delete=models.CASCADE)
    valor = models.DecimalField('Valor', max_digits=5, decimal_places=2)

    imagem_width = models.PositiveIntegerField(null=True, blank=True)
    imagem_height = models.PositiveIntegerField(null=True, blank=True)
    imagem = PictureField(
        'Imagem',
        upload_to='sobremesa',
        width_field='imagem_width',
        height_field='imagem_height',
    )

    class Meta:
        verbose_name = 'Sobremesa'
        verbose_name_plural = 'Sobremesas'

    def __str__(self):
        return self.nome