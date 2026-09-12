# Pacote que agrupa os apps do projeto.
#
# Este arquivo não é decorativo: a partir do Python 3.11 o unittest deixou
# de descobrir testes dentro de "namespace packages" (diretórios sem
# __init__.py). Sem ele, "manage.py test" encontraria zero testes e passaria
# — o pior tipo de suíte verde.
