from rest_framework import generics, permissions
from app_evalpro_api.models import Subject
from app_evalpro_api.serializers import SubjectSerializer

class SubjectListCreateView(generics.ListCreateAPIView):
    serializer_class = SubjectSerializer
    # Obligamos a que tengan un token válido (estar logueados)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Si es administrador, tal vez quieras que vea TODAS las materias
        if user.groups.filter(name='administrador').exists():
            return Subject.objects.all()
            
        # Si es maestro, SOLO ve las materias que él creó
        return Subject.objects.filter(created_by=user)

    def perform_create(self, serializer):
        # Al crear la materia, le asignamos automáticamente como dueño al usuario del token
        serializer.save(created_by=self.request.user)