"""
Configuração do projeto restaurant-manager.

Todo valor sensível ou que muda entre ambientes vem de variável de ambiente
(arquivo .env na raiz, lido por python-decouple). Nenhum segredo real é
versionado; use .env.example como modelo.

Documentação das decisões: docs/ARQUITETURA.md
"""
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Segurança básica
# ---------------------------------------------------------------------------
# DEBUG falso por padrão: um clone novo nunca sobe acidentalmente em modo de
# depuração. O script de preparação do ambiente escreve DEBUG=True no .env local.
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

# Em desenvolvimento aceitamos uma chave de conveniência para não travar a
# primeira execução; em qualquer outro caso a chave é obrigatória.
SECRET_KEY = config('DJANGO_SECRET_KEY', default='')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-insecure-key-nao-use-fora-do-desenvolvimento'
    else:
        raise RuntimeError(
            'DJANGO_SECRET_KEY não definida. Copie .env.example para .env e '
            'gere uma chave com: python -c "from django.core.management.utils '
            'import get_random_secret_key; print(get_random_secret_key())"'
        )

ALLOWED_HOSTS = config(
    'DJANGO_ALLOWED_HOSTS',
    default='127.0.0.1,localhost',
    cast=Csv(),
)

# Origens confiáveis para CSRF. Necessário quando o servidor é acessado por
# outro host/porta (ex.: celular na mesma rede -> http://192.168.0.10:8000).
CSRF_TRUSTED_ORIGINS = config('DJANGO_CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# ---------------------------------------------------------------------------
# Aplicações
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'apps.clientes',
    'apps.cardapio',
    'apps.atendimento',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.atendimento.context_processors.perfil_do_usuario',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
# Uma única configuração, deliberadamente: SQLite.
# Justificativa e limites de concorrência em docs/ARQUITETURA.md.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': config('DJANGO_DB_PATH', default=str(BASE_DIR / 'db.sqlite3')),
        'OPTIONS': {
            # Espera até 15s por um lock em vez de falhar imediatamente, e
            # mantém a checagem de chaves estrangeiras ligada.
            'timeout': 15,
            'init_command': 'PRAGMA foreign_keys=ON;',
            'transaction_mode': 'IMMEDIATE',
        },
        'ATOMIC_REQUESTS': False,
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
LOGIN_URL = '/entrar/'
LOGIN_REDIRECT_URL = '/apos-login/'
LOGOUT_REDIRECT_URL = '/'

# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Arquivos estáticos e de mídia
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # Compressão sim, manifesto com hash no nome não. O manifesto exigiria
    # rodar collectstatic antes de qualquer coisa que renderize um template
    # (inclusive os testes), e o ganho de cache não compensa essa amarração
    # em um projeto deste tamanho.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# Em desenvolvimento o WhiteNoise serve direto das pastas de origem, sem exigir
# que collectstatic já tenha rodado (senão ele avisa "No directory at:
# staticfiles/" a cada requisição). Em produção, quem serve é o STATIC_ROOT.
if DEBUG:
    WHITENOISE_USE_FINDERS = True
    WHITENOISE_AUTOREFRESH = True

# Limites de upload: o catálogo aceita imagem de produto, nada além disso.
DATA_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024      # 3 MB por requisição
FILE_UPLOAD_MAX_MEMORY_SIZE = 3 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500

# ---------------------------------------------------------------------------
# Cabeçalhos e cookies de segurança
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
# O token CSRF é lido por JavaScript nas telas de garçom e caixa, então o
# cookie de CSRF não pode ser HttpOnly. Ele não é credencial de sessão.
CSRF_COOKIE_HTTPONLY = False

# Sessão expira ao fechar o navegador do salão e caduca em 12 horas.
SESSION_COOKIE_AGE = 60 * 60 * 12
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Ligue apenas quando a aplicação estiver atrás de HTTPS. Em demonstração
# local (http://127.0.0.1:8000) manter em False é o que permite o login.
SECURE_COOKIES = config('DJANGO_SECURE_COOKIES', default=False, cast=bool)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES

SECURE_SSL_REDIRECT = config('DJANGO_SECURE_SSL_REDIRECT', default=False, cast=bool)
if SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Erros vão para o console do servidor com stack trace; o usuário final recebe
# apenas uma mensagem genérica (ver apps/atendimento/api.py).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simples': {'format': '[{asctime}] {levelname} {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simples'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'ERROR', 'propagate': False},
        'atendimento': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# ---------------------------------------------------------------------------
# Regras de negócio configuráveis
# ---------------------------------------------------------------------------
# Quantidade máxima aceita em um item de comanda. Documentado no README.
ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM = config(
    'ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM', default=99, cast=int
)
# Regra de cobrança de produto meio a meio: 'maior' ou 'media'.
ATENDIMENTO_REGRA_MEIO_A_MEIO = config('ATENDIMENTO_REGRA_MEIO_A_MEIO', default='maior')
