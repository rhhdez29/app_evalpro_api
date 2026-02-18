from django.contrib import admin
from app_evalpro_api.models import Teacher, Student, Administrator

@admin.register(Administrator)
class AdministratorAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "id_admin", "faculty", "creation")
    search_fields = ("user__email", "user__first_name", "id_admin", "faculty")

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "id_teacher", "faculty", "creation", "update")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "id_teacher")

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "id_student", "career", "semester", "kardex", "creation")
    search_fields = ("user__email", "user__first_name", "id_student", "career")