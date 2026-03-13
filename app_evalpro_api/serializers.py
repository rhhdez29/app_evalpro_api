from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Teacher, Student, Administrator, Subject, Exam, Question, AnswerOption

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")

class AdministratorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Administrator
        fields = ('id', 'user', 'id_admin', 'department', 'creation', 'update')
        read_only_fields = ('id', 'creation', 'update')

class TeacherSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Teacher
        fields = ('id', 'user', 'id_teacher', 'faculty', 'creation', 'update')
        read_only_fields = ('id', 'creation', 'update')

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Student
        fields = ('id', 'user', 'id_student', 'career', 'semester', 'kardex', 'creation', 'update')
        read_only_fields = ('id', 'creation', 'update')

class SubjectListSerializer(serializers.ModelSerializer):
    # Campos calculados al vuelo (Solo lectura)
    teacher_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    exams_count = serializers.SerializerMethodField()

    # Nota: exams_count lo agregaremos cuando creemos la tabla Exam

    class Meta:
        model = Subject
        fields = (
            'id',
            'name',
            'code', 
            'color',
            'department', 
            'teacher_name', 
            'students_count', 
            'exams_count'
        )
        # Protegemos los campos que no deben enviarse en el POST
        read_only_fields = ('id', 'created_by', 'teacher_name', 'students_count')

    def get_teacher_name(self, obj):
        # Une el nombre y apellido del creador
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"
    
    def get_students_count(self, obj):
        # Verifica si la relación 'students' ya existe en el modelo Subject
        if hasattr(obj, 'students'):            
            return obj.students.count()
        
        return 10
    def get_exams_count(self, obj):
        if hasattr(obj, 'exams'):
            return obj.exams.count()
        
        return 0
    
class SubjectDetailSerializer(serializers.ModelSerializer):
    # Calculamos los datos extra que tu Angular está esperando
    teacher_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    exams_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        # Asegúrate de que los nombres de los campos coincidan con la interfaz de tu Angular
        fields = [
            'id', 
            'name', 
            'code', 
            'color', 
            'department', 
            'teacher_name', 
            'students_count', 
            'exams_count'
        ]

    # Funciones para calcular los campos dinámicos:
    def get_teacher_name(self, obj):
        if obj.created_by:
            # Asumiendo que teacher tiene relación con el modelo User
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return "Sin profesor asignado"

    def get_students_count(self, obj):
        # Verifica si la relación 'students' ya existe en el modelo Subject
        if hasattr(obj, 'students'):            
            return obj.students.count()
        
        return 0

    def get_exams_count(self, obj):
        # Verifica si la relación 'exams' ya existe en el modelo Subject
        if hasattr(obj, 'exams'):
            return obj.exams.count()
        
        # Si aún no existe la tabla/relación, devolvemos 0 de forma segura
        return 0
    

class AswerQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = [
            'id', 
            'question', 
            'text', 
            'is_correct'
        ]

class QuestionSerializer(serializers.ModelSerializer):

    options = AswerQuestionSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = [
            'id',
            'exam',
            'question_type',
            'prompt',
            'points',
            'order',
            'metadata',
            'options'
        ]

class ExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = [
            'id',
            'title',
            'subject',
            'description',
            'start_date',
            'end_date',
            'total_score',
            'status',
            'duration_minutes',
            'questions'
        ]

class ExamListSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id',
            'title',
            'description',
            'start_date',
            'end_date',
            'duration_minutes',
            'status',
            'questions_count'
        ]

    def get_questions_count(self, obj):
        if hasattr(obj, 'questions'):
            return obj.questions.count()
        
        return 0
    