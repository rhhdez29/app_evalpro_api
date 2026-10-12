import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from app_evalpro_api.models import Administrator, EmailVerification, Exam, Student, Teacher


class CustomAuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(label="Usuario o Email", write_only=True)
    password = serializers.CharField(
        label="Contraseña",
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    token = serializers.CharField(label="Token", read_only=True)

    def validate(self, attrs):
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        if not username or not password:
            raise serializers.ValidationError(
                {"error": "Debes proporcionar usuario/email y contraseña."},
                code='authorization'
            )

        # Buscar usuario por username o email
        candidate_user = User.objects.filter(
            Q(username=username) | Q(email=username)
        ).first()

        if candidate_user and candidate_user.check_password(password):
            # 1. Si user.is_active == False: Cuenta suspendida administrativamente
            if not candidate_user.is_active:
                raise AuthenticationFailed('Cuenta suspendida por un administrador')

            # 2. Si user.is_active == True PERO user.is_email_verified == False: Cuenta no verificada
            if not candidate_user.is_email_verified:
                raise AuthenticationFailed({
                    'detail': 'Cuenta no verificada',
                    'code': 'unverified_email',
                    'email': candidate_user.email
                })

            attrs['user'] = candidate_user
            return attrs

        # 3. Credenciales inválidas
        raise serializers.ValidationError(
            {"error": "Credenciales inválidas. Verifica tu usuario y contraseña."},
            code='authorization'
        )


class CustomAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        
        try:
            serializer.is_valid(raise_exception=True)
        except AuthenticationFailed as exc:
            if isinstance(exc.detail, dict):
                return Response(exc.detail, status=status.HTTP_403_FORBIDDEN)
            return Response(
                {
                    'detail': str(exc.detail),
                    'error': str(exc.detail),
                    'code': 'account_suspended'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except serializers.ValidationError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        
        teacher = getattr(user, 'teacher_profile', None)
        
        if teacher:
            estado = teacher.status
            if estado == 'pending':
                return Response(
                    {"error": "Tu cuenta no ha sido aprobada por el administrador."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if estado == 'rejected':
                return Response(
                    {"error": "Tu cuenta ha sido rechazada por el administrador."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        role_names = [role.name for role in user.groups.all()]

        administrator = getattr(user, 'admin_profile', None)
        teacher = getattr(user, 'teacher_profile', None)
        student = getattr(user, 'student_profile', None)

        if not administrator and not teacher and not student:
            return Response(
                {"error": "No se encontró el perfil para este usuario."},
                status=status.HTTP_404_NOT_FOUND
            )

        token, created = Token.objects.get_or_create(user=user)

        response_data = {
            'id': user.pk,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'token': token.key,
            'roles': role_names,
        }

        # Campos específicos según rol
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
            
            # Calcular exámenes próximos (ventana de 48 horas o ya iniciados)
            now = timezone.now()
            two_days_later = now + timedelta(days=2)
            upcoming_exams_count = Exam.objects.filter(
                subject__in=student.enrolled_subjects.all(),
                status='scheduled',
            ).filter(
                Q(start_date__range=(now, two_days_later)) | 
                Q(end_date__range=(now, two_days_later)) |
                Q(start_date__lte=now, end_date__gte=now)
            ).exclude(
                attempts__student=student,
                attempts__status__in=['completed', 'annulled_by_fraud', 'annulled']
            ).count()
            
            response_data['upcoming_exams_count'] = upcoming_exams_count

        return Response(response_data)


class Logout(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_active:
            Token.objects.filter(user=user).delete()
            return Response({'logout': True})

        return Response({'logout': False})


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip()
        otp_code = str(request.data.get('otp_code', '')).strip()

        if not email or not otp_code:
            return Response(
                {"error": "Debes proporcionar 'email' y 'otp_code'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "El usuario no existe o el código es inválido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active:
            return Response(
                {"error": "Esta cuenta está suspendida por un administrador."},
                status=status.HTTP_403_FORBIDDEN
            )

        verification = getattr(user, 'email_verification', None)
        if not verification or not verification.otp_code:
            return Response(
                {"error": "No hay un código OTP activo para este usuario o la cuenta ya fue verificada."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if verification.otp_code != otp_code:
            return Response(
                {"error": "El código OTP es incorrecto."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Activación exitosa: marcamos is_email_verified = True y dejamos is_active en paz
        verification.is_email_verified = True
        verification.otp_code = None
        verification.save()

        return Response(
            {"message": "Cuenta verificada exitosamente. Ahora puedes iniciar sesión."},
            status=status.HTTP_200_OK
        )


class ResendOtpView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip()

        if not email:
            return Response(
                {"error": "Debes proporcionar el campo 'email'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "No existe ningún usuario registrado con ese correo electrónico."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Si la cuenta está suspendida, no debe enviar ningún correo
        if not user.is_active:
            return Response(
                {"error": "Esta cuenta ha sido suspendida por un administrador."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Si ya está verificada
        if user.is_email_verified:
            return Response(
                {"message": "Esta cuenta ya está verificada. Puedes iniciar sesión."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generar nuevo OTP de 6 dígitos solo si is_email_verified == False y is_active == True
        otp_code = f"{random.randint(100000, 999999)}"
        EmailVerification.objects.update_or_create(
            user=user,
            defaults={'otp_code': otp_code, 'is_email_verified': False}
        )

        # Enviar correo simulado
        send_mail(
            subject="Código de verificación reenviado - EvalPro",
            message=f"Tu nuevo código de verificación es: {otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(
            {"message": "Código de verificación reenviado exitosamente."},
            status=status.HTTP_200_OK
        )
