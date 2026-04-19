from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from app_evalpro_api.serializers import UserListSerializer
from django.contrib.auth import get_user_model
from rest_framework.decorators import action
from rest_framework.response import Response
from app_evalpro_api.models import Teacher
from app_evalpro_api.serializers import PendingTeacherSerializer
from rest_framework import status
from .permissions import IsRoleAdmin

User = get_user_model()

# Usamos ReadOnlyModelViewSet porque esta vista solo es para LISTAR y VER DETALLE.
# La creación de usuarios usualmente va en otro endpoint de registro.
class UserListViewSet(viewsets.ModelViewSet):

    #Consulta a la base de datos
    queryset = User.objects.all().order_by('-date_joined')
    
    #Método para obtener el serializador dependiendo de la acción
    def get_serializer_class(self):
        if self.action == 'pending_teachers':
            return PendingTeacherSerializer
        return UserListSerializer
    
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
        
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    #Acción para obtener los docentes pendientes de aprobación
    @action(detail=False, methods=['get'])
    def pending_teachers(self, request):
        
        #Consulta a la base de datos
        pending_teachers = Teacher.objects.filter(
            status='pending'
        ).select_related('user').order_by('-user__date_joined')

        #Paginación
        page = self.paginate_queryset(pending_teachers)

        #Serialización
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(pending_teachers, many=True)
        return Response(serializer.data)

    #Acción para cambiar el estado de un usuario
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

    #ENDPOINT PARA ACEPTAR/RECHAZAR
    @action(detail=True, methods=['patch'])
    def review_teacher(self, request, pk=None):
        # 1. Obtenemos al usuario por el ID de la URL
        user = self.get_object()
        
        # 2. Leemos la decisión que nos manda Angular desde el body
        new_status = request.data.get('status')
        
        # Validamos que no nos manden basura
        if new_status not in ['approved', 'rejected']:
            return Response(
                {"error": "Estado inválido. Solo se permite 'approved' o 'rejected'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Verificamos que este usuario realmente tenga un perfil de maestro
        teacher = getattr(user, 'teacher_profile', None)
        if not teacher:
            return Response(
                {"error": "Este usuario no tiene un perfil de maestro registrado."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. APLICAMOS LA REGLA DE NEGOCIO
        # Actualizamos la tabla Teacher
        teacher.status = new_status
        teacher.save()

        # 5. Devolvemos el usuario actualizado para que Angular lo procese
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)