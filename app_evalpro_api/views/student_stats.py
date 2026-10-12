from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Avg
from app_evalpro_api.models import Student, ExamAttempt

class StudentStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. Obtener perfil de alumno asociado al usuario autenticado
        student = getattr(request.user, 'student_profile', None)
        if not student:
            student = Student.objects.filter(user=request.user).first()

        if not student:
            return Response(
                {"error": "El usuario autenticado no cuenta con perfil de estudiante."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Consultar todos los intentos de examen completados del estudiante
        completed_attempts = (
            ExamAttempt.objects.filter(student=student, status='completed')
            .select_related('exam', 'exam__subject')
            .order_by('-end_time', '-id')
        )

        total_exams = completed_attempts.count()

        # 3. Manejar el caso donde aún no hay exámenes completados (evitando división por cero)
        if total_exams == 0:
            return Response({
                "total_exams": 0,
                "average_score": 0.0,
                "passed_exams": 0,
                "failed_exams": 0,
                "pass_rate": 0.0,
                "by_subject": [],
                "recent_attempts": []
            }, status=status.HTTP_200_OK)

        # 4. Cálculos globales
        passed_exams = completed_attempts.filter(score__gte=60).count()
        failed_exams = total_exams - passed_exams

        avg_score_val = completed_attempts.aggregate(avg=Avg('score'))['avg']
        average_score = round(float(avg_score_val), 2) if avg_score_val is not None else 0.0
        pass_rate = round((passed_exams / total_exams) * 100, 1)

        # 5. Agrupación por materia
        subject_stats = {}
        for attempt in completed_attempts:
            subject = attempt.exam.subject
            subj_id = subject.id
            if subj_id not in subject_stats:
                subject_stats[subj_id] = {
                    "subject_id": subj_id,
                    "subject_name": subject.name,
                    "subject_code": subject.code,
                    "color": subject.color,
                    "scores": []
                }
            if attempt.score is not None:
                subject_stats[subj_id]["scores"].append(float(attempt.score))

        by_subject = []
        for subj_id, data in subject_stats.items():
            scores = data["scores"]
            count = len(scores)
            avg = round(sum(scores) / count, 2) if count > 0 else 0.0
            by_subject.append({
                "subject_id": subj_id,
                "subject_name": data["subject_name"],
                "subject_code": data["subject_code"],
                "color": data["color"],
                "exams_count": count,
                "average_score": avg
            })

        by_subject.sort(key=lambda s: s["subject_name"])

        # 6. Intentos recientes (hasta 6)
        recent_attempts = []
        for attempt in completed_attempts[:6]:
            date_val = attempt.end_time or attempt.start_time
            recent_attempts.append({
                "id": attempt.id,
                "exam_id": attempt.exam.id,
                "exam_title": attempt.exam.title,
                "subject_name": attempt.exam.subject.name,
                "score": float(attempt.score) if attempt.score is not None else 0.0,
                "date": date_val.isoformat() if date_val else None,
                "is_passed": (attempt.score is not None and float(attempt.score) >= 60.0)
            })

        return Response({
            "total_exams": total_exams,
            "average_score": average_score,
            "passed_exams": passed_exams,
            "failed_exams": failed_exams,
            "pass_rate": pass_rate,
            "by_subject": by_subject,
            "recent_attempts": recent_attempts
        }, status=status.HTTP_200_OK)
