
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions
from app_evalpro_api.models import Subject, SubjectEnrollment, Student, Exam
from app_evalpro_api.serializers import SubjectListSerializer, SubjectDetailSerializer, EnrolledStudentSerializer, ExamDetailSerializer, ExamListSerializer, StudentPendingExamSerializer
from rest_framework.response import Response
from rest_framework.decorators import action

class SubjectViewSet(viewsets.ModelViewSet):

    # Protegemos la ruta para que solo usuarios logueados la vean
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Subject.objects.none()

        # Si es administrador, se veran TODAS las materias
        if user.groups.filter(name='administrador').exists():
            return Subject.objects.all()

        # Si es Maestro, ve solo las materias que ÉL creó
        if hasattr(user, 'teacher_profile'):
            return Subject.objects.filter(created_by=user)
            
        # Si es Alumno, ve solo las materias donde está INSCRITO
        if hasattr(user, 'student_profile'):
            return Subject.objects.filter(students=user.student_profile)

        return Subject.objects.none()

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
        
        user = request.user

        is_admin = user.groups.filter(name='administrador').exists()
        is_creator = subject.created_by == user
        
        if not (is_admin or is_creator):
            return Response(
                {"error": "No tienes permiso para eliminar esta materia."},
                status=status.HTTP_403_FORBIDDEN
            )
        subject.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        # 1. Obtenemos la materia de la URL (ej: /api/subjects/5/add_student/)
        subject = self.get_object()
        user = request.user
        
        # 2. Seguridad: Solo el creador de la materia o un admin pueden agregar alumnos
        is_creator = subject.created_by == user
        is_admin = user.groups.filter(name='administrador').exists()
        
        if not (is_creator or is_admin):
            return Response(
                {"error": "No tienes permiso para agregar alumnos a esta materia."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Leemos la matrícula que el frontend nos manda en el Body
        email_alumno = request.data.get('email')
        
        if not email_alumno:
            return Response(
                {"error": "Debes proporcionar la matrícula (id_student) del alumno."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Buscamos al alumno navegando a través de su usuario (user__email)
        try:
            student = Student.objects.get(user__email=email_alumno)
            
            # Verificamos si ya está inscrito
            if subject.students.filter(id=student.id).exists():
                return Response(
                    {"error": "Este alumno ya está inscrito en la materia."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Lo agregamos
            subject.students.add(student)
            
            # student.user.first_name saca el nombre desde la tabla User
            nombre_alumno = student.user.first_name or student.user.username
            
            return Response(
                {"message": f"Alumno {nombre_alumno} agregado exitosamente a la materia."}, 
                status=status.HTTP_200_OK
            )
            
        except Student.DoesNotExist:
            return Response(
                {"error": f"No se encontró ningún alumno registrado con el correo: {email_alumno}."}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def enrolled_students(self, request, pk=None):
        # 1. Obtenemos la materia
        subject = self.get_object()
        
        # 2. Obtenemos todos los estudiantes vinculados a esta materia
        enrollments = SubjectEnrollment.objects.filter(
            subject=subject
        ).select_related('student__user')
        #3. si no hay alumnos lanzamos ese mensaje
        if not enrollments.exists():
            return Response(
                ([])
            )

        # 4. Si hay alumnos mandamos la lista 
        serializer = EnrolledStudentSerializer(enrollments, many=True)
        
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def student_exams(self, request, pk=None):
        # 1. Obtenemos la materia de la URL
        subject = self.get_object()
        user = request.user

        # 2. Verificamos que el usuario logueado sea un alumno
        if not hasattr(user, 'student_profile'):
            return Response(
                {"error": "Solo los alumnos pueden acceder a esta sección."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student = request.user.student_profile

        # 3. SEGURIDAD: Verificamos que el alumno esté inscrito en esta materia
        is_enrolled = SubjectEnrollment.objects.filter(
            subject=subject, 
            student=student
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "No tienes permiso para ver los exámenes de esta materia porque no estás inscrito."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. Obtenemos solo los exámenes publicados
        exams = Exam.objects.filter(
            subject=subject,
            status='draft' #Muestra solo los exámenes que esten en estado draft. Por implementar el cambio de estado en angular
        )

        # 5. Verificamos si hay exámenes
        if not exams.exists():
            return Response(
                {"message": "Aún no hay exámenes disponibles para esta materia."},
                status=status.HTTP_200_OK
            )

        # 6. Serializamos y devolvemos la lista
        serializer = StudentPendingExamSerializer(exams, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)