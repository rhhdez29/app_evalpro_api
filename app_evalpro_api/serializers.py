from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Teacher, Student, Administrator, Subject

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

class SubjectSerializer(serializers.ModelSerializer):
    # Campos calculados al vuelo (Solo lectura)
    teacher_name = serializers.SerializerMethodField()
    students_count = serializers.IntegerField(source='students.count', read_only=True)
    
    # Nota: exams_count lo agregaremos cuando creemos la tabla Exam

    class Meta:
        model = Subject
        fields = (
            'id', 'name', 'code', 'department', 'color', 
            'created_by', 'teacher_name', 'students_count', 'students'
        )
        # Protegemos los campos que no deben enviarse en el POST
        read_only_fields = ('id', 'created_by', 'teacher_name', 'students_count')

    def get_teacher_name(self, obj):
        # Une el nombre y apellido del creador
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"