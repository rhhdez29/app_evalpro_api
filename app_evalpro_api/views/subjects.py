
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions
from app_evalpro_api.models import Subject
from app_evalpro_api.serializers import SubjectListSerializer, SubjectDetailSerializer
from rest_framework.response import Response

class SubjectViewSet(viewsets.ModelViewSet):

    # Protegemos la ruta para que solo usuarios logueados la vean
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user

        # Si es administrador, se veran TODAS las materias
        if user.groups.filter(name='administrador').exists():
            return Subject.objects.all()
            
        # Si es maestro, SOLO ve las materias que él creó
        return Subject.objects.filter(created_by=user)

    def get_serializer_class(self):
        # este serializador pesado solo cuando piden el detalle (ID)
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        
        # Si es un GET normal (lista), puedes retornar un SubjectListSerializer más básico
        return SubjectListSerializer
    
    def perform_create(self, serializer):
        # Al crear la materia, le asignamos automáticamente como dueño al usuario del token
        serializer.save(created_by=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        subject = self.get_object()
        
        if subject.created_by != request.user:
            return Response(
                {"error": "No tienes permiso para eliminar esta materia."},
                status=status.HTTP_403_FORBIDDEN
            )
        subject.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)