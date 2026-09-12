"""
Carga de dados fictícios para demonstração.

Idempotente: pode rodar quantas vezes quiser sem duplicar nada — tudo usa
get_or_create pela chave natural (nome da categoria, nome do produto dentro da
categoria, número da mesa, username). Não apaga nada e não mexe em comandas.

    python manage.py seed_demo
    python manage.py seed_demo --sem-usuarios
    python manage.py seed_demo --senha "outraSenha123"
"""
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.atendimento import perfis
from apps.atendimento.models import Mesa
from apps.cardapio.models import Adicional, Categoria, Produto

SENHA_PADRAO_DEMO = 'demo12345'

CATEGORIAS = [
    ('Lanches', 10),
    ('Pizzas', 20),
    ('Bebidas', 30),
    ('Sobremesas', 40),
]

PRODUTOS = [
    # (categoria, nome, descrição, preço, meio a meio)
    ('Lanches', 'X-Salada', 'Pão, hambúrguer, queijo, alface e tomate', '26.00', False),
    ('Lanches', 'X-Bacon', 'Pão, hambúrguer, queijo e bacon crocante', '32.50', False),
    ('Lanches', 'Tortilla de frango', 'Tortilla recheada com frango desfiado', '29.90', False),
    ('Pizzas', 'Pizza Calabresa', 'Calabresa, cebola e orégano', '58.00', True),
    ('Pizzas', 'Pizza Portuguesa', 'Presunto, ovo, cebola, ervilha e azeitona', '62.00', True),
    ('Pizzas', 'Pizza Marguerita', 'Muçarela, tomate e manjericão', '55.00', True),
    ('Pizzas', 'Pizza Brigadeiro', 'Chocolate, granulado e leite condensado', '49.00', True),
    ('Bebidas', 'Refrigerante lata 350ml', 'Cola, guaraná ou laranja', '7.00', False),
    ('Bebidas', 'Cerveja long neck', 'Long neck 355ml gelada', '12.00', False),
    ('Bebidas', 'Suco natural 400ml', 'Laranja, limão ou maracujá', '11.50', False),
    ('Bebidas', 'Água mineral 500ml', 'Com ou sem gás', '5.00', False),
    ('Sobremesas', 'Pudim de leite', 'Fatia individual', '14.00', False),
    ('Sobremesas', 'Petit gateau', 'Com sorvete de creme', '22.00', False),
]

ADICIONAIS = [
    # (nome, preço, categorias)
    ('Bacon extra', '6.00', ['Lanches']),
    ('Queijo extra', '4.50', ['Lanches']),
    ('Ovo', '3.00', ['Lanches']),
    ('Borda de catupiry', '10.00', ['Pizzas']),
    ('Borda de cheddar', '10.00', ['Pizzas']),
    ('Gelo e limão', '2.00', ['Bebidas']),
]

USUARIOS = [
    # (username, nome, sobrenome, grupo, is_staff)
    ('garcom', 'Ana', 'Garçom', perfis.GARCOM, False),
    ('garcom2', 'Bruno', 'Garçom', perfis.GARCOM, False),
    ('caixa', 'Carla', 'Caixa', perfis.CAIXA, False),
    ('gerente', 'Diego', 'Gerente', perfis.ADMINISTRACAO, True),
]

QUANTIDADE_DE_MESAS = 12


class Command(BaseCommand):
    help = 'Cria dados fictícios de demonstração. Pode ser executado várias vezes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sem-usuarios',
            action='store_true',
            help='Não cria os usuários de demonstração (apenas catálogo e mesas).',
        )
        parser.add_argument(
            '--senha',
            default=SENHA_PADRAO_DEMO,
            help=f'Senha dos usuários de demonstração (padrão: {SENHA_PADRAO_DEMO}).',
        )
        parser.add_argument(
            '--mesas',
            type=int,
            default=QUANTIDADE_DE_MESAS,
            help=f'Quantidade de mesas a garantir (padrão: {QUANTIDADE_DE_MESAS}).',
        )

    @transaction.atomic
    def handle(self, *args, **opcoes):
        criados = {'categorias': 0, 'produtos': 0, 'adicionais': 0, 'mesas': 0, 'usuarios': 0}

        self.stdout.write('Sincronizando grupos e permissões…')
        resumo_grupos = perfis.sincronizar_grupos()
        for nome, total in resumo_grupos.items():
            self.stdout.write(f'  {nome}: {total} permissões')

        categorias = {}
        for nome, ordem in CATEGORIAS:
            categoria, nova = Categoria.objects.get_or_create(
                nome=nome, defaults={'ordem': ordem}
            )
            categorias[nome] = categoria
            criados['categorias'] += int(nova)

        for nome_categoria, nome, descricao, preco, meio_a_meio in PRODUTOS:
            _, novo = Produto.objects.get_or_create(
                categoria=categorias[nome_categoria],
                nome=nome,
                defaults={
                    'descricao': descricao,
                    'preco': Decimal(preco),
                    'permite_meio_a_meio': meio_a_meio,
                },
            )
            criados['produtos'] += int(novo)

        for nome, preco, nomes_categorias in ADICIONAIS:
            adicional, novo = Adicional.objects.get_or_create(
                nome=nome, defaults={'preco': Decimal(preco)}
            )
            adicional.categorias.set([categorias[n] for n in nomes_categorias])
            criados['adicionais'] += int(novo)

        for numero in range(1, opcoes['mesas'] + 1):
            _, nova = Mesa.objects.get_or_create(numero=numero, defaults={'lugares': 4})
            criados['mesas'] += int(nova)

        if not opcoes['sem_usuarios']:
            senha = opcoes['senha']
            for username, nome, sobrenome, grupo_nome, is_staff in USUARIOS:
                usuario, novo = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'first_name': nome,
                        'last_name': sobrenome,
                        'is_staff': is_staff,
                    },
                )
                if novo:
                    # set_password gera o hash do Django; senha nunca é gravada em texto.
                    usuario.set_password(senha)
                    usuario.save()
                    criados['usuarios'] += 1
                grupo = Group.objects.get(name=grupo_nome)
                usuario.groups.add(grupo)

        self.stdout.write(self.style.SUCCESS('Dados de demonstração prontos.'))
        self.stdout.write(
            '  criados agora: '
            + ', '.join(f'{chave}={valor}' for chave, valor in criados.items())
        )
        if not opcoes['sem_usuarios']:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    'Usuários de demonstração (garcom, garcom2, caixa, gerente) usam a senha '
                    f'"{opcoes["senha"]}". São credenciais de demonstração local: troque-as '
                    'antes de qualquer publicação.'
                )
            )
