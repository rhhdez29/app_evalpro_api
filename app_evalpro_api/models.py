from django.db import models
from django.contrib.auth.models import User
from rest_framework.authentication import TokenAuthentication
from django.utils import timezone

class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"

class Administrator(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Importante: el related_name "admin_profile" es la clave para la autenticación
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    
    # Datos específicos del administrador (equivalentes a id_teacher y faculty)
    id_admin = models.CharField(max_length=50, unique=True, verbose_name="ID del Administrador")
    faculty = models.CharField(max_length=255, verbose_name="Facultad")
    
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Admin: {self.user.first_name} {self.user.last_name} - {self.faculty}"

class Teacher(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('active', 'Activo'),
        ('rejected', 'Rechazado')
    )

    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    id_teacher = models.CharField(max_length=50, unique=True, verbose_name="Matrícula/ID del Maestro")
    faculty = models.CharField(max_length=255, verbose_name="Facultad")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Maestro: {self.user.first_name} {self.user.last_name} - {self.faculty}"

class Student(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")

    # Datos específicos del alumno
    id_student = models.CharField(max_length=50, unique=True, verbose_name="Matrícula del Alumno")
    career = models.CharField(max_length=255, verbose_name="Carrera")
    semester = models.CharField(max_length=20, verbose_name="Semestre")
    
    # Manejo del archivo Kárdex
    # upload_to le dice a Django en qué subcarpeta guardar el archivo
    kardex = models.FileField(upload_to='kardex_pdfs/', null=True, blank=True, verbose_name="Kárdex PDF")
    
    creation = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Alumno: {self.user.first_name} {self.user.last_name} - {self.career}"

class Subject(models.Model):
    id = models.BigAutoField(primary_key=True)

    #Datos de la materia
    name = models.CharField(max_length=255, verbose_name="Nombre de la Materia")
    code = models.CharField(max_length=20, verbose_name="Código de la Materia")
    department = models.CharField(max_length=255, verbose_name="Departamento/Area")

    #color recuadro materia
    color = models.CharField(max_length=50, default="bg-blue-500", verbose_name="Color Materia")

    #Relacion con el creador Admin o Maestro
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_subjects",
        verbose_name="Creado por"
    )

    # Relación con los alumnos (Muchos alumnos pueden tener muchas materias)
    # blank=True permite que al crear la materia pueda estar vacía (sin alumnos aún)
    students = models.ManyToManyField(
        Student, 
        blank=True, 
        through='SubjectEnrollment',
        related_name="enrolled_subjects",
        verbose_name="Alumnos Inscritos"
    )

    # Campos de auditoría
    creation = models.DateTimeField(auto_now_add=True)
    update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
    
class Exam(models.Model):

    STATUS_EXAM = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('published', 'Published'),
        ('closed', 'Closed')
    )

    #Relaciones
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='exams')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_exams')

    #Campos base

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    #fechas y tiempo
    start_date = models.DateTimeField(help_text='Fecha y hora en que se abre el examen')
    end_date = models.DateTimeField(help_text='Fecha y hora en que se cierra el examen')
    duration_minutes = models.PositiveIntegerField(help_text='Duración del examen en minutos')
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text='Puntaje total del examen')
    status = models.CharField(max_length=20, choices=STATUS_EXAM, default='draft', help_text='Estado del examen')

    def __str__(self):
        return f"{self.title}-{self.subject.name}"

    @property
    def current_status(self):
        # Si el maestro lo tiene en borrador, siempre es borrador
        if self.status == 'draft':
            return 'draft'
            
        # Si está programado, dejamos que el tiempo decida
        if self.status == 'scheduled':
            now = timezone.now()
            
            # Si ya pasó la fecha de inicio y no ha pasado la de fin
            if self.start_date <= now <= self.end_date:
                return 'published'
                
            # Si ya pasó la fecha de fin
            elif now > self.end_date:
                return 'closed'
                
            # Si aún no llega la fecha de inicio
            return 'scheduled'
            
        return self.status    
class Question(models.Model):
    #Tipos de preguntas
    QUESTION_TYPES =(
        ('MCQ', 'Multiple Choice'),
        ('TF', 'True/False'),
        ('MATCH','Statement Matching'),
        ('CODE', 'Code Editor')
    )

    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)

    #Texto principal
    prompt = models.TextField()

    #puntos que vale la pregunta
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)

    #Aqui guardamos la configuracion espefica dependiendo del tipo de pregunta
    metadata = models.JSONField(default=dict, blank=True, help_text='Configuracion espeficica del tipo de pregunta')

    order = models.PositiveIntegerField(default=0, help_text='Orden de la pregunta en el examen')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_question_type_display()} - {self.prompt[:30]}"
    
class AnswerOption(models.Model):
    question = models.ForeignKey(Question ,on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    partial_points = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return self.text

class SubjectEnrollment(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    
    date_enrolled = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subject', 'student')
        ordering = ['-date_enrolled']

# El intento del examen 
class ExamAttempt(models.Model):
    # Relaciones principales
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE, related_name='attempts')
    
    # Tiempos
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(auto_now=True) 
    
    # Estados de calificación
    status = models.CharField(
        max_length=20, 
        choices=[
            ('in_progress', 'En progreso'), 
            ('needs_grading', 'Pendiente de calificación'), 
            ('completed', 'Completado')
        ],
        default='in_progress'
    )
    
    # Calificación total (Se llena al terminar o al calificar manualmente)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        # Esto es lo que bloquea que el alumno mande el examen dos veces
        unique_together = ('student', 'exam') 

    def __str__(self):
        return f"Intento de {self.student.user.first_name} en {self.exam.title}"


# LA RESPUESTA INDIVIDUAL
class StudentAnswer(models.Model):
    # Pertenece a un intento específico, no al examen directo
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    
    # Los dos tipos de respuestas posibles (una o la otra)
    selected_option = models.ForeignKey('AnswerOption', on_delete=models.SET_NULL, null=True, blank=True)
    text_response = models.TextField(null=True, blank=True)
    
    # Datos de evaluación por pregunta
    is_correct = models.BooleanField(null=True, blank=True) # Null significa "No calificada aún"
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Bandera de alerta para el maestro
    needs_manual_review = models.BooleanField(default=False)

    class Meta:
        # Un alumno no puede contestar la misma pregunta dos veces en el mismo intento
        unique_together = ('attempt', 'question')

    def save(self, *args, **kwargs):
        # 🛡️ Lógica de Autocalificación
        if self.is_correct is None:
            tipo_pregunta = self.question.question_type 
            
            # 1. TIPO: OPCIÓN MÚLTIPLE (MCQ)
            if tipo_pregunta == 'MCQ':
                # Validamos si seleccionó una opción y si esa opción en la BD tiene is_correct=True
                if self.selected_option and getattr(self.selected_option, 'is_correct', False):
                    self.is_correct = True
                    self.points_earned = self.question.points
                else:
                    self.is_correct = False
                    self.points_earned = 0.00
                self.needs_manual_review = False
                
            # 2. TIPO: VERDADERO / FALSO (TF)
            elif tipo_pregunta == 'TF':
                # El alumno envía "true" o "false" en text_response.
                # La BD tiene { correctAnswer: true } como booleano en el JSON.
                respuesta_alumno = str(self.text_response).strip().lower()
                respuesta_correcta = str(self.question.metadata.get('correctAnswer', '')).strip().lower()
                
                if respuesta_alumno == respuesta_correcta:
                    self.is_correct = True
                    self.points_earned = self.question.points
                else:
                    self.is_correct = False
                    self.points_earned = 0.00
                self.needs_manual_review = False

            # 3. TIPO: RELACIONAR (MATCH)
            elif tipo_pregunta == 'MATCH':
                import json
                try:
                    # Parseamos lo que envía el alumno desde Angular
                    respuesta_alumno = json.loads(self.text_response)
                    
                    # Obtenemos el arreglo original de pares: [{left: "int", right: "..."}, ...]
                    pares_correctos = self.question.metadata.get('pairs', [])
                    
                    # Convertimos los pares originales a un diccionario para fácil comparación
                    # Ej: {"int": "Número entero", "str": "Texto..."}
                    dict_correcto = {str(item.get('left')).strip(): str(item.get('right')).strip() for item in pares_correctos}
                    
                    # Flexibilidad: soportar si Angular manda un array de objetos o un diccionario directo
                    if isinstance(respuesta_alumno, list):
                        dict_alumno = {str(item.get('left')).strip(): str(item.get('right')).strip() for item in respuesta_alumno}
                    else:
                        dict_alumno = {str(k).strip(): str(v).strip() for k, v in respuesta_alumno.items()}
                    
                    # La magia: Python compara que ambos diccionarios tengan exactamente las mismas llaves y valores, sin importar el orden
                    if dict_alumno == dict_correcto:
                        self.is_correct = True
                        self.points_earned = self.question.points
                    else:
                        self.is_correct = False
                        self.points_earned = 0.00
                        
                except (ValueError, TypeError, AttributeError):
                    # Si mandó algo que no es JSON válido o hubo un error de formato
                    self.is_correct = False
                    self.points_earned = 0.00
                    
                self.needs_manual_review = False
                
            # 4. TIPO: CÓDIGO (CODE)
            elif tipo_pregunta == 'CODE':
                # Se va directo a calificación manual
                self.is_correct = None 
                self.points_earned = 0.00
                self.needs_manual_review = True
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Respuesta a Pregunta {self.question.id} (Intento {self.attempt.id})"