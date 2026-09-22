from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from app_evalpro_api.models import (
    Teacher, Administrator, Student, Subject, SubjectEnrollment, Exam, Question, AnswerOption
)

class Command(BaseCommand):
    help = 'Inserta datos de prueba (10 alumnos, 1 materia de pruebas, 3 exámenes con preguntas variadas) de forma segura.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Iniciando Seeding de Datos de Prueba ==="))

        # 1. Obtener o crear el usuario creador (Maestro o Admin)
        creator_user = None
        teacher = Teacher.objects.filter(status='active').first()
        if teacher:
            creator_user = teacher.user
            self.stdout.write(f"✓ Usando maestro existente: {creator_user.get_full_name() or creator_user.username} ({creator_user.email})")
        else:
            admin = Administrator.objects.first()
            if admin:
                creator_user = admin.user
                self.stdout.write(f"✓ Usando administrador existente: {creator_user.get_full_name() or creator_user.username} ({creator_user.email})")
            else:
                teacher_user, created = User.objects.get_or_create(
                    username="test_maestro@test.com",
                    defaults={
                        'email': "test_maestro@test.com",
                        'first_name': "Maestro",
                        'last_name': "Pruebas",
                        'is_staff': True
                    }
                )
                if created:
                    teacher_user.set_password("evalpro2026")
                    teacher_user.save()
                    Teacher.objects.create(
                        user=teacher_user,
                        id_teacher="EMP1001",
                        faculty="Facultad de Ingeniería",
                        status="active"
                    )
                    self.stdout.write("✓ Creado maestro de prueba por defecto: test_maestro@test.com / evalpro2026")
                creator_user = teacher_user

        # 2. Crear 10 estudiantes
        self.stdout.write("\n--- Creando / Verificando 10 Estudiantes ---")
        students_created = []
        student_credentials = []

        for i in range(1, 11):
            email = f"test_alumno_{i}@test.com"
            username = email
            id_student = f"TEST{i:03d}"

            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f"Alumno{i}",
                    'last_name': f"Test",
                }
            )

            if user_created:
                user.set_password("evalpro2026")
                user.save()

            student, student_created = Student.objects.get_or_create(
                user=user,
                defaults={
                    'id_student': id_student,
                    'career': "Ingeniería en Sistemas Computacionales",
                    'semester': "5to Semestre"
                }
            )

            students_created.append(student)
            student_credentials.append((email, "evalpro2026", id_student, "Creado" if user_created else "Existente"))

        self.stdout.write(f"✓ Se procesaron {len(students_created)} alumnos exitosamente.")

        # 3. Crear Materia de Pruebas
        self.stdout.write("\n--- Creando / Verificando Materia de Pruebas ---")
        subject, subj_created = Subject.objects.get_or_create(
            code="TEST101",
            defaults={
                'name': "Materia de Pruebas",
                'department': "Ciencias de la Computación",
                'color': "bg-indigo-600",
                'created_by': creator_user
            }
        )
        if subj_created:
            self.stdout.write(self.style.SUCCESS(f"✓ Materia '{subject.name}' ({subject.code}) creada."))
        else:
            self.stdout.write(f"✓ Materia '{subject.name}' ({subject.code}) ya existía.")

        # Inscribir a los 10 alumnos en la materia
        enrolled_count = 0
        for student in students_created:
            enrollment, created = SubjectEnrollment.objects.get_or_create(
                subject=subject,
                student=student
            )
            if created:
                enrolled_count += 1

        self.stdout.write(f"✓ Inscritos {len(students_created)} alumnos en '{subject.name}' ({enrolled_count} nuevas inscripciones).")

        # 4. Crear 3 Exámenes con preguntas
        self.stdout.write("\n--- Creando / Verificando 3 Exámenes ---")
        now = timezone.now()
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=30)

        exams_data = [
            {
                "title": "Simulacro de Redes",
                "description": "Examen de prueba sobre conceptos de redes informáticas, modelo OSI y protocolos.",
                "duration": 60,
                "questions": [
                    {
                        "prompt": "¿Cuál es la capa del modelo OSI encargada del direccionamiento IP y enrutamiento de paquetes?",
                        "type": "MCQ",
                        "points": 30.00,
                        "options": [
                            ("Capa de Red (Network)", True),
                            ("Capa de Enlace de Datos", False),
                            ("Capa de Transporte", False),
                            ("Capa de Aplicación", False)
                        ]
                    },
                    {
                        "prompt": "El protocolo TCP es un protocolo no orientado a conexión.",
                        "type": "TF",
                        "points": 30.00,
                        "options": [
                            ("Falso", True),
                            ("Verdadero", False)
                        ]
                    },
                    {
                        "prompt": "Escribe una función en Python `validar_ip(ip)` que devuelva `True` si una cadena recibida tiene un formato IPv4 válido.",
                        "type": "CODE",
                        "points": 40.00,
                        "metadata": {
                            "language": "python",
                            "initial_code": "def validar_ip(ip):\n    # Tu código aquí\n    pass"
                        }
                    }
                ]
            },
            {
                "title": "Examen de Algoritmos",
                "description": "Evaluación práctica de estructuras de datos, complejidad algorítmica y programación.",
                "duration": 90,
                "questions": [
                    {
                        "prompt": "¿Cuál es la complejidad temporal promedio del algoritmo QuickSort?",
                        "type": "MCQ",
                        "points": 30.00,
                        "options": [
                            ("O(n log n)", True),
                            ("O(n^2)", False),
                            ("O(n)", False),
                            ("O(1)", False)
                        ]
                    },
                    {
                        "prompt": "Una estructura de datos de tipo Pila (Stack) sigue el principio FIFO (First In, First Out).",
                        "type": "TF",
                        "points": 30.00,
                        "options": [
                            ("Falso", True),
                            ("Verdadero", False)
                        ]
                    },
                    {
                        "prompt": "Implementa la función `fibonacci(n)` que devuelva el n-ésimo número de la sucesión de Fibonacci de manera eficiente.",
                        "type": "CODE",
                        "points": 40.00,
                        "metadata": {
                            "language": "python",
                            "initial_code": "def fibonacci(n):\n    # Tu solución aquí\n    pass"
                        }
                    }
                ]
            },
            {
                "title": "Prueba de Base de Datos",
                "description": "Examen sobre modelos relacionales, consultas SQL y normalización.",
                "duration": 45,
                "questions": [
                    {
                        "prompt": "¿Qué cláusula SQL se utiliza para filtrar los resultados de una agregación con `GROUP BY`?",
                        "type": "MCQ",
                        "points": 30.00,
                        "options": [
                            ("HAVING", True),
                            ("WHERE", False),
                            ("ORDER BY", False),
                            ("FILTER BY", False)
                        ]
                    },
                    {
                        "prompt": "Una Clave Foránea (Foreign Key) puede contener valores NULL en una tabla relacional.",
                        "type": "TF",
                        "points": 30.00,
                        "options": [
                            ("Verdadero", True),
                            ("Falso", False)
                        ]
                    },
                    {
                        "prompt": "Escribe una consulta SQL que obtenga los nombres (`first_name`, `last_name`) de todos los estudiantes registrados.",
                        "type": "CODE",
                        "points": 40.00,
                        "metadata": {
                            "language": "sql",
                            "initial_code": "-- Escribe tu consulta SQL aquí\nSELECT first_name, last_name FROM app_evalpro_api_student;"
                        }
                    }
                ]
            }
        ]

        for exam_info in exams_data:
            exam, exam_created = Exam.objects.get_or_create(
                title=exam_info["title"],
                subject=subject,
                defaults={
                    'description': exam_info["description"],
                    'start_date': start_date,
                    'end_date': end_date,
                    'duration_minutes': exam_info["duration"],
                    'total_score': 100.00,
                    'status': 'published',
                    'created_by': creator_user
                }
            )

            status_str = "creado" if exam_created else "existente"
            self.stdout.write(f"\n  • Examen: '{exam.title}' ({status_str})")

            # Crear preguntas del examen
            for idx, q_info in enumerate(exam_info["questions"], start=1):
                question, q_created = Question.objects.get_or_create(
                    exam=exam,
                    prompt=q_info["prompt"],
                    defaults={
                        'question_type': q_info["type"],
                        'points': q_info["points"],
                        'metadata': q_info.get("metadata", {}),
                        'order': idx
                    }
                )

                if "options" in q_info:
                    for opt_text, is_corr in q_info["options"]:
                        AnswerOption.objects.get_or_create(
                            question=question,
                            text=opt_text,
                            defaults={'is_correct': is_corr}
                        )

                q_status = "creada" if q_created else "existente"
                self.stdout.write(f"    - Pregunta {idx} [{q_info['type']}]: {question.prompt[:45]}... ({q_status})")

        # 5. Imprimir informe final de credenciales
        self.stdout.write(self.style.SUCCESS("\n=========================================================="))
        self.stdout.write(self.style.SUCCESS("  ✓ SEEDING COMPLETADO EXITOSAMENTE"))
        self.stdout.write(self.style.SUCCESS("=========================================================="))
        self.stdout.write("\nCredenciales por defecto de los 10 alumnos inscritos:\n")
        self.stdout.write(f"{'#':<4} {'EMAIL':<30} {'CONTRASEÑA':<15} {'MATRÍCULA':<12} {'ESTADO':<10}")
        self.stdout.write("-" * 75)
        for idx, (email, pwd, mat, state) in enumerate(student_credentials, start=1):
            self.stdout.write(f"{idx:<4} {email:<30} {pwd:<15} {mat:<12} {state:<10}")
        self.stdout.write("-" * 75)
        self.stdout.write(self.style.SUCCESS(f"\n✓ Materia vinculada: {subject.name} (Código: {subject.code})"))
        self.stdout.write(self.style.SUCCESS(f"✓ Exámenes vinculados: 3 exámenes publicados con 3 preguntas cada uno."))
        self.stdout.write(self.style.SUCCESS("✓ No se crearon intentos de examen (ExamAttempt)."))
