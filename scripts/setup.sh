#!/usr/bin/env bash
# =============================================================================
#  Preparação do ambiente de desenvolvimento (Linux / macOS)
#
#      bash scripts/setup.sh
#
#  Cria o ambiente virtual, instala as dependências, gera um .env local com
#  SECRET_KEY própria, aplica as migrações e carrega os dados de demonstração.
#  Não apaga nada: se .venv ou .env já existirem, são preservados.
# =============================================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

[ -d .venv ] || python3 -m venv .venv
python=".venv/bin/python"

echo 'Instalando dependências...'
"$python" -m pip install --upgrade pip --quiet
"$python" -m pip install -r requirements-dev.txt --quiet

if [ ! -f .env ]; then
    echo 'Criando .env com uma SECRET_KEY nova...'
    chave="$("$python" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    cat > .env <<EOF
DJANGO_SECRET_KEY=$chave
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_SECURE_COOKIES=False
DJANGO_SECURE_SSL_REDIRECT=False
ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM=99
ATENDIMENTO_REGRA_MEIO_A_MEIO=maior
EOF
else
    echo '.env já existe e foi preservado.'
fi

"$python" manage.py migrate --no-input
"$python" manage.py seed_demo

echo
echo 'Pronto. Para subir o servidor:'
echo '  .venv/bin/python manage.py runserver'
echo
echo 'Usuários de demonstração: garcom, garcom2, caixa, gerente (senha demo12345)'
