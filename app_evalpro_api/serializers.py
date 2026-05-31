from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from .models import Teacher, Student, Administrator, Subject, Exam, Question, AnswerOption, SubjectEnrollment
from django.utils import timezone

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

    status = serializers.CharField(source='current_status', read_only=True)

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
    status = serializers.BooleanField(source='is_active', read_only=True)
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


#Serializador para obtener los docentes pendientes de aprobación
class PendingTeacherSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(source='user.id', read_only=True)

    #Campos del modelo User
    complete_name = serializers.SerializerMethodField()
    email = serializers.CharField(source='user.email', read_only=True)
    role = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    

    class Meta:
        #Modelo Teacher
        model = Teacher
        fields = [
            'id',
            'complete_name',
            'email',
            'faculty',
            'id_teacher',
            'role',
            'date_joined',
            'status',
        ]

    #Método para obtener el nombre completo del usuario
    def get_complete_name(self, obj):
        user = obj.user
        return f"{user.first_name} {user.last_name}"

    #Método para obtener el rol del usuario
    def get_role(self, obj):
        user = obj.user
        grupo = user.groups.first()
        if grupo:
            return grupo.name
        return "Sin Rol"

class EnrolledStudentSerializer(serializers.ModelSerializer):
    # 🌟 1. Corregimos las rutas: Todo debe pasar por 'student' primero
    id = serializers.CharField(source='student.id', read_only=True)
    email = serializers.EmailField(source='student.user.email', read_only=True)

    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"

    date_enrolled = serializers.DateTimeField(
        read_only=True, 
        format="%Y-%m-%d %H:%M"
    )

    class Meta:
        # 🌟 2. Cambiamos Student por SubjectEnrollment
        model = SubjectEnrollment
        fields = ['id', 'name', 'email', 'date_enrolled']


class StudentPendingExamSerializer(serializers.ModelSerializer): 
    # usamos 'source' para renombrarlos al momento de enviar la respuesta.
    dueDate = serializers.DateTimeField(source='end_date', format="%Y-%m-%dT%H:%M:%S", read_only=True) 
    duration = serializers.IntegerField(source='duration_minutes', read_only=True) 
    maxAttempts = serializers.IntegerField(source='max_attempts', read_only=True) 

    # 2. Campos calculados (No vienen directo de una columna, los calculamos aquí)
    questions = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Exam

        fields = ['id', 'title', 'dueDate', 'duration', 'questions', 'attempts', 'maxAttempts', 'status']

    # --- Funciones para los campos calculados ---

    def get_questions(self, obj):
        # Cuenta cuántas preguntas están vinculadas a este examen.
        return obj.questions.count() 

    def get_attempts(self, obj):
        # Para saber los intentos, necesitamos saber QUIÉN está preguntando.
        request = self.context.get('request')
        if request and hasattr(request.user, 'student_profile'):
            student = request.user.student_profile
            # Por implementar el numero de intentos del alumno en esta materia
            return 0 
        return 0

    def get_status(self, obj):
        # Lógica para determinar el estado visual en Angular
        now = timezone.now()

        if obj.end_date and now > obj.end_date:
            return 'overdue'
            
        # Por implementar la logica para 'in-progress' si el alumno ya empezó un intento pero no lo terminó
        
        return 'available'

# 🛡️ 1. Opciones (NIVEL MÁS ALTO DE SEGURIDAD)
class StudentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        # ⚠️ ESTRICTAMENTE PROHIBIDO INCLUIR 'is_correct' o campos similares aquí
        fields = ['id','question','text'] 

# 🛡️ 2. Preguntas
class StudentQuestionSerializer(serializers.ModelSerializer):
    # Anidamos las opciones seguras
    options = StudentOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        # Mandamos el texto y valor, pero nada de justificaciones o configuraciones del maestro
        fields = ['id', 'prompt', 'question_type', 'points', 'metadata', 'options']

# 🛡️ 3. Examen (El cascarón principal)
class StudentExamDetailSerializer(serializers.ModelSerializer):
    # Anidamos las preguntas seguras
    questions = StudentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'total_score', 'duration_minutes', 'questions']