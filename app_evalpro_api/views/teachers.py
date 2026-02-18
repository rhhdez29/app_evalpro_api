from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth.models import Group, User
from app_evalpro_api.models import Teacher
from app_evalpro_api.serializers import TeacherSerializer

class TeachersView(generics.CreateAPIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Extraer datos del JSON
        role = data.get('rol', 'maestro')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')
        id_teacher = data.get('id_teacher')
        faculty = data.get('faculty')

        # Verificamos si el correo ya existe
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return Response({"message": f"El usuario con el email {email} ya existe"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Creamos el usuario nativo de Django
        user = User.objects.create(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True
        )
        user.set_password(password) # Encriptamos contraseña
        user.save()

        # 2. Asignamos el grupo (Rol)
        group, created = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        # 3. Creamos el perfil de Maestro y lo vinculamos al usuario
        teacher = Teacher.objects.create(
            user=user,
            id_teacher=id_teacher,
            faculty=faculty
        )

        return Response({"profile_created_id": teacher.id, "message": "Maestro registrado exitosamente"}, status=status.HTTP_201_CREATED)
