from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from app_evalpro_api.models import Exam, Question, AnswerOption
from app_evalpro_api.serializers import (ExamDetailSerializer, ExamListSerializer, QuestionSerializer, AswerQuestionSerializer, StudentExamDetailSerializer)
from rest_framework.response import Response
from rest_framework.decorators import action
from app_evalpro_api.models import Student, SubjectEnrollment
from django.shortcuts import get_object_or_404



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

        # 4. Validar el estado del examen (¿Ya venció? ¿Está publicado?)
        # if exam.status != 'publicado': ... 
        
        # 5. Serializar con el blindaje de seguridad
        serializer = StudentExamDetailSerializer(exam)
        
        return Response(serializer.data, status=status.HTTP_200_OK)

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