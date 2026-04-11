from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from app_evalpro_api.serializers import UserListSerializer
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsRoleAdmin

User = get_user_model()

# Usamos ReadOnlyModelViewSet porque esta vista solo es para LISTAR y VER DETALLE.
# La creación de usuarios usualmente va en otro endpoint de registro.
class UserListViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserListSerializer
    
    #Solo usuarios con role 'administrador' pueden entrar
    permission_classes = [IsRoleAdmin]

    #Sobrescribimos el método destroy para agregar validación
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        #Validación: No permitir borrarse a sí mismo
        if user == request.user:
            return Response(
                {"error": "No puedes eliminarte a ti mismo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        usuario.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        user = self.get_object()
    
        #Validación: No permitir desactivarse a sí mismo
        if user == request.user:
            return Response(
                {"error": "No puedes desactivarte a ti mismo"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = not user.is_active
        user.save()
        
        return Response(
            {"message": "Usuario actualizado correctamente"},
            status=status.HTTP_200_OK
        )