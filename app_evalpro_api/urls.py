from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Importamos nuestras vistas refactorizadas
from .views.bootstrap import VersionView
from .views.teachers import TeachersView
from .views.students import StudentsView
from .views.subjects import SubjectListCreateView
from .views.auth import CustomAuthToken, Logout

urlpatterns = [
    
    path('admin/', admin.site.urls),

    # Endpoints para Maestros
    path("teachers/", TeachersView.as_view(), name="teacher-register"),
    
    # Endpoints para Alumnos
    path("students/", StudentsView.as_view(), name="student-register"),

    #Enpoint para materias
    path("subjects/", SubjectListCreateView.as_view(), name="subject-list-create"),

    #login
    path("login/", CustomAuthToken.as_view(), name="login"),
    
    path("logout/", Logout.as_view(), name="logout")
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)