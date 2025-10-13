from django.shortcuts import redirect
from django.urls import reverse

class AdminRedirectMiddleware:
    """
    Se um usuário autenticado acessar /admin/ (não superuser),
    redireciona para a página conforme o grupo:
      - GrupoCaixa -> /funcionarios/caixa/
      - GrupoGarcon -> /funcionarios/comanda/
    Superusers continuam no admin.
    Evita loop verificando if request.path startswith target.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Middleware só atua quando o usuário já está autenticado
        user = getattr(request, 'user', None)

        # Caminhos do admin principal (poderá ajustar se admin estiver em outra URL)
        admin_root_paths = (reverse('admin:index'), reverse('admin:logout'))  # '/admin/' e '/admin/logout/'
        # reverse('admin:index') normalmente é '/admin/'

        # Se o request.path estiver exatamente no admin index (ou '/admin'), e o user está autenticado
        if user and user.is_authenticated and not user.is_superuser:
            path = request.path
            # Se está tentando acessar admin index (ou '/admin' sem barra), redireciona conforme grupo
            # Evita redirecionar se já estiver nas páginas de destino (loop)
            if path.rstrip('/') == reverse('admin:index').rstrip('/'):
                # se for do grupo caixa
                if user.groups.filter(name='GrupoCaixa').exists():
                    target = reverse('funcionarios:caixa')
                    if not path.startswith(target):
                        return redirect(target)
                # se for do grupo garçom
                elif user.groups.filter(name='GrupoGarcon').exists() or user.groups.filter(name='GrupoGarçom').exists():
                    # aceitamos 'GrupoGarcon' ou 'GrupoGarçom' por precaução
                    target = reverse('funcionarios:comanda')
                    if not path.startswith(target):
                        return redirect(target)
                # se não pertence a nenhum grupo, deixamos ir para admin (ou poderia negar)
        return self.get_response(request)
