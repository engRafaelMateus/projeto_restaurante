from allauth.socialaccount.providers.mediawiki.provider import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('apps.clientes.urls')),
    path('accounts/', include('allauth.urls')),
    path('pedidos/', include('apps.pedidos.urls')),
    path('funcionarios/', include('apps.funcionarios.urls')),
    path('pictures/', include('pictures.urls', namespace='pictures')),

    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
