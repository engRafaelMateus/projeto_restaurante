from django.db import models
from pictures.models import PictureField
from django.contrib.auth.models import User


class Base(models.Model):
    criado = models.DateTimeField('Criação', auto_now_add=True)
    modificado = models.DateTimeField('Modificado', auto_now=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        abstract = True

class Funcionario(Base):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Usuário do Sistema"
    )
    nome = models.CharField(max_length=50)
    login = models.CharField(max_length=20)
    senha = models.CharField(max_length=15)

    class Meta:
        verbose_name = 'Funcionario'
        verbose_name_plural = 'Funcionarios'

    def __str__(self):
        return self.nome


class ConfiguracaoMesas(models.Model):
    quantidade_mesas = models.PositiveIntegerField(default=10, verbose_name="Quantidade de Mesas")

    class Meta:
        verbose_name = "Configuração de Mesas"
        verbose_name_plural = "Configuração de Mesas"

    def __str__(self):
        return f"{self.quantidade_mesas} mesas configuradas"


class Mesa(Base):
    numero = models.IntegerField()
    status = models.CharField(
        max_length=10,
        choices=[('livre', 'Livre'), ('ocupada', 'Ocupada')],
        default='livre')

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero']

    def __str__(self):
        return f"Mesa {self.numero}"


class Pedido(Base):
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE)
    itens = models.JSONField()
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('aberto', 'Aberto'), ('fechado', 'Fechado')],
        default='aberto'
    )

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f"Pedido Mesa {self.mesa.numero}"