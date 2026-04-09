from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from app_evalpro_api.serializers import UserListSerializer
from django.contrib.auth import get_user_model
from .permissions import IsRoleAdmin

User = get_user_model()

# Usamos ReadOnlyModelViewSet porque esta vista solo es para LISTAR y VER DETALLE.
# La creación de usuarios usualmente va en otro endpoint de registro.
class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserListSerializer
    
    #Solo usuarios con is_staff=True o is_superuser=True pueden entrar
    permission_classes = [IsRoleAdmin]