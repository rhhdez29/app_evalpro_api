from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from app_evalpro_api.models import Exam, Question, AnswerOption
from app_evalpro_api.serializers import (ExamDetailSerializer, ExamListSerializer, QuestionSerializer, AswerQuestionSerializer, StudentExamDetailSerializer, SubmitExamSerializer, ExamAttemptReviewSerializer)
from rest_framework.response import Response
from rest_framework.decorators import action
from app_evalpro_api.models import Student, SubjectEnrollment, Exam, ExamAttempt, StudentAnswer, AnswerOption, Question
from django.shortcuts import get_object_or_404
from django.db import transaction


class ExamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Exam.objects.none() 

        # Si es administrador vera todos los examenes
        if user.groups.filter(name='administrador').exists():
            queryset = Exam.objects.all()
        else:
            queryset = Exam.objects.filter(created_by=user)

        materia_id = self.request.query_params.get('subject', None) 
        
        if materia_id is not None:
            #Filtramos el queryset que ya paso por la seguridad del maestro
            queryset = queryset.filter(subject_id=materia_id)

        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ExamListSerializer
        
        return ExamDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        exam = self.get_object()

        if exam.created_by != request.user:
            return Response(
                {"error": "No tienes permiso para eliminar este examen."},
                status=status.HTTP_403_FORBIDDEN
            )
        exam.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def take_exam(self, request, pk=None):
        # 1. Obtenemos el examen solicitado
        exam = get_object_or_404(Exam, pk=pk)
        
        # 2. Obtenemos al estudiante
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {"error": "Solo los alumnos registrados pueden tomar exámenes."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. SEGURIDAD VITAL: ¿El alumno está en la materia de este examen?
        is_enrolled = SubjectEnrollment.objects.filter(
            subject=exam.subject, 
            student=student
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "No estás inscrito en la materia de este examen."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Buscamos si el alumno ya tiene un intento previo para este examen
        attempt = ExamAttempt.objects.filter(exam=exam, student=student).first()
        
        if attempt:
            # Si el examen ya está terminado, calificado o anulado, le bloqueamos el acceso
            if attempt.status in ['completed', 'needs_grading', 'annulled_by_fraud']:
                return Response(
                    {"error": "Este examen ya fue completado o anulado. No puedes volver a ingresar."},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Si está 'in_progress', no hacemos nada (solo recargó la página)
        else:
            # Si no existe, es su primera vez entrando. 
            # ¡Damos el banderazo de salida y guardamos la hora oficial!
            attempt = ExamAttempt.objects.create(
                student=student,
                exam=exam,
                status='in_progress'
            )
        
        # 5. Serializar con el blindaje de seguridad
        serializer = StudentExamDetailSerializer(exam)
        response_data = serializer.data
        
        # Inyectamos datos extra del intento para que Angular pueda pintar el reloj correctamente
        response_data['attempt_id'] = attempt.id
        response_data['server_start_time'] = attempt.start_time 
        
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        # 1. Obtenemos el examen
        exam = self.get_object()

        # 2. SEGURIDAD: Verificar que quien intenta cambiar el estado sea el creador
        if exam.created_by != request.user:
            return Response(
                {"error": "No tienes permiso para modificar el estado de este examen."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Leer el nuevo estado desde el cuerpo (body) de la petición
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {"error": "Debes proporcionar el campo 'status'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_status = new_status.lower()
        
        # 4. Validar que el estado sea correcto
        allowed_statuses = ['draft', 'scheduled'] 
        
        if new_status not in allowed_statuses:
            return Response(
                {"error": f"Estado inválido. Opciones permitidas: {allowed_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Actualizar y guardar en la base de datos
        exam.status = new_status
        exam.save()

        # 6. Devolver una respuesta de éxito para Angular
        return Response(
            {
                "message": "Estado actualizado correctamente",
                "status": exam.status
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        exam = get_object_or_404(Exam, pk=pk)
        
        # 1. Validar que quien envía sea un alumno
        try:
            student = request.user.student_profile
        except AttributeError:
            return Response(
                {"error": "Solo los alumnos registrados pueden enviar exámenes."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. SEGURIDAD: Evitar envíos duplicados
        if ExamAttempt.objects.filter(student=student, exam=exam).exists():
            return Response(
                {"error": "Ya has enviado tus respuestas para este examen anteriormente."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validar que el JSON de Angular venga bien estructurado
        serializer = SubmitExamSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 4. 🛡️ Iniciar la Transacción Segura
        try:
            with transaction.atomic():
                # A. Crear la "Hoja de respuestas" (El Intento)
                attempt = ExamAttempt.objects.create(
                    student=student, 
                    exam=exam, 
                    status='in_progress'
                )

                respuestas_data = serializer.validated_data['answers']
                requiere_revision_manual = False
                calificacion_temporal = 0.00

                # B. Iterar sobre el arreglo y procesar pregunta por pregunta
                for resp_data in respuestas_data:
                    question = get_object_or_404(Question, id=resp_data['question_id'])
                    
                    # Buscar la opción solo si el alumno seleccionó una
                    option = None
                    if resp_data.get('selected_option_id'):
                        option = get_object_or_404(AnswerOption, id=resp_data['selected_option_id'])

                    # 🌟 AL CREAR ESTO, TU MODELO EJECUTA EL .save() Y SE AUTOCALIFICA
                    student_answer = StudentAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=option,
                        text_response=resp_data.get('text_response')
                    )

                    # C. Leer el resultado de la autocalificación del modelo
                    if student_answer.needs_manual_review:
                        requiere_revision_manual = True
                    else:
                        calificacion_temporal += float(student_answer.points_earned)

                # D. Finalizar el examen determinando su estado final
                attempt.score = calificacion_temporal
                attempt.status = 'needs_grading' if requiere_revision_manual else 'completed'
                attempt.save()

            # 5. Respuesta de éxito para que Angular muestre la pantalla de "Terminado"
            return Response({
                "message": "Examen enviado y guardado con éxito.",
                "attempt_id": attempt.id,
                "status": attempt.status,
                "score": attempt.score if attempt.status == 'completed' else "Pendiente de revisión del profesor"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Si hay CUALQUIER error en el for, la base de datos aborta y no guarda datos basura
            return Response(
                {"error": f"Ocurrió un error interno al guardar el examen: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def my_result(self, request, pk=None):

        from django.shortcuts import get_object_or_404
        from app_evalpro_api.models import Exam
        
        exam = get_object_or_404(Exam, pk=pk)
        
        # 1. Obtener al estudiante actual
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {"error": "Solo los alumnos pueden ver resultados."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Buscar el intento de este estudiante para este examen
        try:
            attempt = ExamAttempt.objects.get(exam=exam, student=student)
        except ExamAttempt.DoesNotExist:
            return Response(
                {"error": "Aún no has contestado este examen."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Serializar y enviar
        serializer = ExamAttemptReviewSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #Elimina la respuesta del estudiante
    @action(detail=True, methods=['delete'])
    def reset_attempt(self, request, pk=None):
        # 1. Buscamos el examen saltando los filtros del ViewSet
        from django.shortcuts import get_object_or_404
        from app_evalpro_api.models import Exam, ExamAttempt, Student
        
        exam = get_object_or_404(Exam, pk=pk)
        
        # 2. Obtenemos al estudiante actual
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {"error": "Solo los alumnos pueden reiniciar sus intentos."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Buscamos y destruimos el intento
        try:
            attempt = ExamAttempt.objects.get(exam=exam, student=student)
            attempt.delete() # 🌟 Esta línea hace la magia y borra todo en cascada
            return Response(
                {"message": "Intento eliminado con éxito. Puedes volver a tomar el examen."}, 
                status=status.HTTP_200_OK
            )
        except ExamAttempt.DoesNotExist:
            return Response(
                {"message": "No tenías ningún intento guardado para este examen."}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        from app_evalpro_api.models import Exam, ExamAttempt, Student
        
        exam = get_object_or_404(Exam, pk=pk)
        
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {"error": "Solo los alumnos pueden tener intentos."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            attempt = ExamAttempt.objects.get(exam=exam, student=student)
            attempt.status = ExamAttempt.AttemptStatus.ANNULLED_BY_FRAUD
            attempt.cancellation_reason = request.data.get('reason', 'Fraude detectado: pérdida de foco')
            attempt.save()
            
            return Response(
                {"message": "Intento de examen anulado."}, 
                status=status.HTTP_200_OK
            )
        except ExamAttempt.DoesNotExist:
            return Response(
                {"error": "No se encontró un intento para este examen."}, 
                status=status.HTTP_404_NOT_FOUND
            )

class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Question.objects.none()

        # 1. PERMISOS BASE
        if user.groups.filter(name='administrador').exists():
            queryset = Question.objects.all()
        else:
            # De la Pregunta, ve al Examen (exam__), luego a la Materia (subject__), 
            # y verifica si el creador es el usuario actual.
            # (Recuerda cambiar 'created_by' por 'teacher' si así se llama en tu modelo)
            queryset = Question.objects.filter(exam__subject__created_by=user)

        # 2. EL FILTRO PARA ANGULAR
        # Cuando Angular necesite pintar el examen 15, hará: GET /api/questions/?exam=15
        exam_id = self.request.query_params.get('exam', None)
        
        if exam_id is not None:
            # Filtramos para que solo devuelva las preguntas de ese examen en específico
            queryset = queryset.filter(exam_id=exam_id)

        return queryset
    
class AnswerOptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AswerQuestionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='administrador').exists():
            return AnswerOption.objects.all()
        
        return AnswerOption.objects.filter(question__exam__subject__created_by=user)