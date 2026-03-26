from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Importamos nuestras vistas refactorizadas
from .views.bootstrap import VersionView
from .views.teachers import TeachersView
from .views.students import StudentsView
from .views.subjects import SubjectViewSet
from .views.exams import ExamViewSet, QuestionViewSet, AnswerOptionViewSet
from .views.auth import CustomAuthToken, Logout

# Creamos el enrutador de DRF
router = DefaultRouter()

router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'exams', ExamViewSet, basename='exam');
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'options', AnswerOptionViewSet, basename='option')

# {{http}}://{{host}}/exams/?subject=4 obtener los examenes de una materia
# {{http}}://{{host}}/exams/10/ obtener un examen por id
# {{http}}://{{host}}/exams/ obtener todos los examenes

urlpatterns = [
    
    path('', include(router.urls)),

    path('admin/', admin.site.urls),

    # Endpoints para Maestros
    path("teachers/", TeachersView.as_view(), name="teacher-register"),
    
    # Endpoints para Alumnos
    path("students/", StudentsView.as_view(), name="student-register"),

    #login
    path("login/", CustomAuthToken.as_view(), name="login"),
    
    path("logout/", Logout.as_view(), name="logout")
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)