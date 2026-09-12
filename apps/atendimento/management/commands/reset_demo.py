"""
Apaga os dados de operação para reiniciar uma demonstração.

Comando separado do seed de propósito: nada é apagado ao iniciar a aplicação
nem ao carregar dados fictícios. Exige `--confirmar` explícito e recusa rodar
com DEBUG desligado, para não ser executado por engano contra um ambiente que
não seja de demonstração.

    python manage.py reset_demo --confirmar
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.atendimento.models import Comanda, Envio, ItemComanda, Pagamento


class Command(BaseCommand):
    help = 'Apaga comandas, itens, envios e pagamentos (apenas ambiente de demonstração).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Obrigatório. Sem esta opção o comando não apaga nada.',
        )
        parser.add_argument(
            '--forcar-fora-de-debug',
            action='store_true',
            help='Permite rodar com DEBUG=False. Use por sua conta e risco.',
        )

    @transaction.atomic
    def handle(self, *args, **opcoes):
        if not opcoes['confirmar']:
            raise CommandError(
                'Nada foi apagado. Rode novamente com --confirmar se é isso mesmo que você quer.'
            )
        if not settings.DEBUG and not opcoes['forcar_fora_de_debug']:
            raise CommandError(
                'DEBUG está desligado: este ambiente não parece ser de demonstração. '
                'Use --forcar-fora-de-debug se tiver certeza.'
            )

        contagem = {
            'pagamentos': Pagamento.objects.count(),
            'itens': ItemComanda.objects.count(),
            'envios': Envio.objects.count(),
            'comandas': Comanda.objects.count(),
        }

        # Ordem importa: as chaves estrangeiras são PROTECT.
        Pagamento.objects.all().delete()
        ItemComanda.objects.all().delete()
        Envio.objects.all().delete()
        Comanda.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                'Operação reiniciada: '
                + ', '.join(f'{chave}={valor}' for chave, valor in contagem.items())
            )
        )
        self.stdout.write('Catálogo, mesas e usuários foram preservados.')
