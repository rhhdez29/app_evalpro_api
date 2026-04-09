from django.contrib.auth.models import User
from django.db import transaction
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

    id = serializers.IntegerField(required=False, allow_null=True)
    question = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = AnswerOption
        fields = [
            'id', 
            'question', 
            'text', 
            'is_correct', 
            'partial_points'
        ]

class QuestionSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(required=False, allow_null=True)
    options = AswerQuestionSerializer(many=True, required=False)
    exam = serializers.PrimaryKeyRelatedField(read_only=True)
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
    questions = QuestionSerializer(many=True, read_only=False)

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

    @transaction.atomic #si falla una pregunta, no se guarda el examen a medias
    def create(self, validated_data):

        # 2. Extraemos el arreglo de preguntas del paquete de datos
        questions_data = validated_data.pop('questions', [])

        # 3. Creamos la metadata del Examen
        exam = Exam.objects.create(**validated_data)
        
        # 4. Iteramos sobre las preguntas y las creamos enlazándolas al examen
        for question_data in questions_data:

            print(question_data)

            options_data = question_data.pop('options', [])
            
            question = Question.objects.create(exam=exam, **question_data)

            for option_data in options_data:
                AnswerOption.objects.create(question=question, **option_data)
            
        # 5. Devolvemos el examen recién creado (Django se encargará de responder con el JSON)
        return exam

    @transaction.atomic
    def update(self, instance, validated_data):
        #Extraemos las preguntas
        questions_data = validated_data.pop('questions', None)

        #Actualizamos el examen
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        #Actualizamos las preguntas
        if questions_data is not None:
            #Lista para guardar los ids de las preguntas que vienen en el paquete
            incoming_questions_ids = []

            #Iteramos sobre las preguntas
            for q_data in questions_data:
                q_id = q_data.get('id')
                options_data = q_data.pop('options', [])

                #Si la pregunta tiene id, la actualizamos
                if q_id:
                    question = Question.objects.get(id=q_id, exam=instance)
                    for attr, value in q_data.items():
                        setattr(question, attr, value)
                    question.save()

                    incoming_questions_ids.append(question.id)

                else:
                    #Si la pregunta no tiene id, la creamos
                    question = Question.objects.create(exam=instance, **q_data)
                    incoming_questions_ids.append(question.id)

                #Lista para guardar los ids de las opciones
                incoming_options_ids = []
                for opt_data in options_data:
                    opt_id = opt_data.get('id', None)
                
                    #Si la opción tiene id, la actualizamos
                    if opt_id:
                        option = AnswerOption.objects.get(id=opt_id, question=question)
                        for attr, value in opt_data.items():
                            setattr(option, attr, value)
                        option.save()
                        incoming_options_ids.append(option.id)
                    else:
                            #Si la opción no tiene id, la creamos
                        option = AnswerOption.objects.create(question=question, **opt_data)
                        incoming_options_ids.append(option.id)

                #Eliminamos las opciones que no vienen en el paquete
                question.options.exclude(id__in=incoming_options_ids).delete()
            
            #Eliminamos las preguntas que no vienen en el paquete
            instance.questions.exclude(id__in=incoming_questions_ids).delete()
            
        return instance
                    
                    



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
    
class UserListSerializer(serializers.ModelSerializer):

    complete_name = serializers.SerializerMethodField()
    
    status = serializers.BooleanField(source='is_active')
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'complete_name',
            'email',
            'role',
            'status'
        ]

    def get_complete_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_role(self, obj):
        grupo = obj.groups.first()
        if grupo:
            return grupo.name
        return "Sin Rol"