
from allauth.socialaccount.providers.mediawiki.provider import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
                  path('admin/', admin.site.urls),

                  # Rotas dos módulos
                  path('', include('apps.clientes.urls')),
                  path('accounts/', include('allauth.urls')),
                  path('pedidos/', include('apps.pedidos.urls')),
                  path('funcionarios/', include('apps.funcionarios.urls')),
                  path('pictures/', include('pictures.urls', namespace='pictures')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
