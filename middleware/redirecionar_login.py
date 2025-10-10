from django.shortcuts import redirect
from django.urls import reverse


class RedirectAfterLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Verifica se o usuário logou e está no /admin
        if request.path == reverse('admin:index') and request.user.is_authenticated:
            user = request.user

            if user.is_superuser:  # Admin continua no admin
                return response

            # Grupo Caixa → vai para página caixa
            if user.groups.filter(name='GrupoCaixa').exists():
                return redirect('/caixa/')

            # Grupo Garçom → vai para página comanda
            if user.groups.filter(name='GrupoGarcom').exists():
                return redirect('/comanda/')

        return response
