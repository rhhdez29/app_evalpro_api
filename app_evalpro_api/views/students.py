from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
# Importamos los parsers para poder recibir archivos
from rest_framework.parsers import MultiPartParser, FormParser 
from django.contrib.auth.models import Group, User
from app_evalpro_api.models import Student
from app_evalpro_api.serializers import StudentSerializer

class StudentsView(generics.CreateAPIView):
    #Con esto le decimos a Django que vamos a recibir archivos y datos de formulario, no un JSON puro.
    parser_classes = (MultiPartParser, FormParser)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Los datos de texto vienen en request.data
        data = request.data
        
        role = data.get('rol', 'alumno')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        password = data.get('password')
        id_student = data.get('id_student')
        career = data.get('career')
        semester = data.get('semester')
        
        # LOS ARCHIVOS vienen separados en request.FILES
        kardex_file = request.FILES.get('kardex') 

        # Verificamos si el correo ya existe
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            return Response({"message": f"El usuario con el email {email} ya existe"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Creamos el usuario
        user = User.objects.create(
            username=email, email=email, first_name=first_name, last_name=last_name, is_active=True
        )
        user.set_password(password)
        user.save()

        # 2. Asignamos el grupo
        group, created = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        # 3. Creamos el perfil de Alumno
        # Al pasarle kardex_file, Django automáticamente lo guarda en la carpeta y escribe la ruta en la Base de Datos
        student = Student.objects.create(
            user=user,
            id_student=id_student,
            career=career,
            semester=semester,
            kardex=kardex_file 
        )

        return Response({"profile_created_id": student.id, "message": "Alumno registrado exitosamente"}, status=status.HTTP_201_CREATED)