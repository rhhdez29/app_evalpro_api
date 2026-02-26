from django.db import models
from django.contrib.auth.models import User
from rest_framework.authentication import TokenAuthentication

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
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    id_teacher = models.CharField(max_length=50, unique=True, verbose_name="Matrícula/ID del Maestro")
    faculty = models.CharField(max_length=255, verbose_name="Facultad")
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
        related_name="enrolled_subjects",
        verbose_name="Alumnos Inscritos"
    )

    # Campos de auditoría
    creation = models.DateTimeField(auto_now_add=True)
    update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"