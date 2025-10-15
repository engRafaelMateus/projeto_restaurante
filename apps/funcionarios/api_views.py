from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Pedido

def grupo_caixa(user):
    return user.groups.filter(name='GrupoCaixa').exists()

@login_required(login_url='/admin/login/')
@user_passes_test(grupo_caixa, login_url='/admin/')
@require_POST
def fechar_pedido(request, pk):
    try:
        pedido = Pedido.objects.get(pk=pk)
    except Pedido.DoesNotExist:
        return JsonResponse({'error':'Pedido não encontrado'}, status=404)

    pedido.status = 'fechado'
    pedido.save()
    return JsonResponse({'ok': True})
