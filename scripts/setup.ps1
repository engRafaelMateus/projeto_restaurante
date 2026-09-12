# =============================================================================
#  Preparacao do ambiente de desenvolvimento (Windows / PowerShell)
#
#      powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
#  Cria o ambiente virtual, instala as dependencias, gera um .env local com
#  SECRET_KEY propria, aplica as migracoes e carrega os dados de demonstracao.
#  Nao apaga nada: se .venv ou .env ja existirem, sao preservados.
# =============================================================================

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$env:PYTHONUTF8 = '1'

$python = 'python'
& $python --version > $null 2>&1
if ($LASTEXITCODE -ne 0) { $python = 'py' }

if (-not (Test-Path '.venv')) {
    Write-Host 'Criando o ambiente virtual...'
    & $python -m venv .venv
}

$venv = Join-Path $raiz '.venv\Scripts\python.exe'

Write-Host 'Instalando dependencias...'
& $venv -m pip install --upgrade pip --quiet
& $venv -m pip install -r requirements-dev.txt --quiet

if (-not (Test-Path '.env')) {
    Write-Host 'Criando .env com uma SECRET_KEY nova...'
    $chave = & $venv -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    @(
        "DJANGO_SECRET_KEY=$chave",
        'DJANGO_DEBUG=True',
        'DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost',
        'DJANGO_SECURE_COOKIES=False',
        'DJANGO_SECURE_SSL_REDIRECT=False',
        'ATENDIMENTO_QUANTIDADE_MAXIMA_POR_ITEM=99',
        'ATENDIMENTO_REGRA_MEIO_A_MEIO=maior'
    ) | Set-Content -Path '.env' -Encoding UTF8
} else {
    Write-Host '.env ja existe e foi preservado.'
}

& $venv manage.py migrate --no-input
& $venv manage.py seed_demo

Write-Host ''
Write-Host 'Pronto. Para subir o servidor:'
Write-Host '  .venv\Scripts\python.exe manage.py runserver'
Write-Host ''
Write-Host 'Usuarios de demonstracao: garcom, garcom2, caixa, gerente (senha demo12345)'
