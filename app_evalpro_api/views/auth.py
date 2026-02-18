from rest_framework import permissions, generics, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from app_evalpro_api.models import Teacher, Student, Administrator

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        if user.is_active:
            role_names = [role.name for role in user.groups.all()]

            # En el futuro aquí podrías validar también si es admin o alumno
            administrator = getattr(user, 'admin_profile', None)
            teacher = getattr(user, 'teacher_profile', None)
            student = getattr(user, 'student_profile', None)

            if not administrator and not teacher and not student:
                return Response({"error": "No se encontró el perfil de Maestro para este usuario."}, status=status.HTTP_404_NOT_FOUND)

            token, created = Token.objects.get_or_create(user=user)

            response_data = {
                'id': user.pk,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'token': token.key,
                'roles': role_names,
            }

            #Campos especificos para maestro y estudiante
            if administrator:
                response_data['id_admin'] = administrator.id_admin
                response_data['faculty'] = administrator.faculty
            if teacher:
                response_data['id_teacher'] = teacher.id_teacher
                response_data['faculty'] = teacher.faculty
            if student:
                response_data['id_student'] = student.id_student
                response_data['career'] = student.career
                response_data['semester'] = student.semester
                # request.build_absolute_uri() crea la URL completa (ej. http://127.0.0.1:8000/media/...)
                response_data['kardex'] = request.build_absolute_uri(student.kardex.url) if student.kardex else None

            return Response(response_data)
            
        return Response({"error": "Cuenta inactiva"}, status=status.HTTP_403_FORBIDDEN)


class Logout(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_active:
            # Eliminamos el token de forma segura
            Token.objects.filter(user=user).delete()
            return Response({'logout': True})

        return Response({'logout': False})
