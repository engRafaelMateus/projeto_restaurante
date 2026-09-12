"""
Mapa de URLs do projeto.

Telas públicas:      /            /cardapio/
Telas de operação:   /atendimento/comanda/   /atendimento/caixa/   /atendimento/historico/
Autenticação:        /entrar/     /sair/     /apos-login/
Administração:       /admin/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.atendimento.views import AposLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('apps.clientes.urls')),
    path('cardapio/', include('apps.cardapio.urls')),
    path('atendimento/', include('apps.atendimento.urls')),

    path(
        'entrar/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('apos-login/', AposLoginView.as_view(), name='apos_login'),
]

# Arquivos de mídia (imagens de produto) servidos pelo Django apenas em
# desenvolvimento. Em produção isso é papel do servidor web.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
