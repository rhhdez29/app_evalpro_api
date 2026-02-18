from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Teacher, Student, Administrator

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