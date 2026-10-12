from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth.models import Group, User
from app_evalpro_api.models import Teacher, EmailVerification
from app_evalpro_api.serializers import TeacherSerializer
import random
from django.conf import settings
from django.core.mail import send_mail

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

        # 1. Creamos el usuario nativo de Django (activo para el framework, pendiente de verificar correo)
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

        # 4. Generamos OTP de 6 dígitos y lo guardamos con is_email_verified=False
        otp_code = f"{random.randint(100000, 999999)}"
        EmailVerification.objects.update_or_create(
            user=user,
            defaults={'otp_code': otp_code, 'is_email_verified': False}
        )

        # 5. Enviamos correo de verificación
        send_mail(
            subject="Código de verificación - EvalPro",
            message=f"Tu código de verificación es: {otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"profile_created_id": teacher.id, "message": "Maestro registrado exitosamente. Por favor verifica tu correo con el código OTP enviado."}, status=status.HTTP_201_CREATED)
