from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Avg
from app_evalpro_api.models import Subject, ExamAttempt

class TeacherPerformanceStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. Obtener todas las materias creadas por el usuario autenticado (profesor o admin)
        subjects = Subject.objects.filter(created_by=request.user).prefetch_related('exams')

        # 2. Obtener todos los intentos completados en exámenes de dichas materias
        attempts = (
            ExamAttempt.objects.filter(exam__subject__in=subjects, status='completed')
            .select_related('exam', 'exam__subject')
        )

        total_attempts = attempts.count()

        # 3. Cálculos globales seguros
        if total_attempts == 0:
            global_average = 0.0
            total_passed = 0
            total_failed = 0
            pass_rate = 0.0
        else:
            total_passed = attempts.filter(score__gte=60).count()
            total_failed = total_attempts - total_passed
            avg_val = attempts.aggregate(avg=Avg('score'))['avg']
            global_average = round(float(avg_val), 2) if avg_val is not None else 0.0
            pass_rate = round((total_passed / total_attempts) * 100, 1)

        # 4. Agrupación y promedio específico por materia
        # Mapeamos los intentos por materia para evitar N+1 queries
        attempts_by_subject = {}
        for att in attempts:
            s_id = att.exam.subject_id
            if s_id not in attempts_by_subject:
                attempts_by_subject[s_id] = []
            if att.score is not None:
                attempts_by_subject[s_id].append(float(att.score))

        subject_averages = []
        for subj in subjects:
            scores = attempts_by_subject.get(subj.id, [])
            sub_attempts_count = len(scores)
            sub_avg = round(sum(scores) / sub_attempts_count, 2) if sub_attempts_count > 0 else 0.0
            
            subject_averages.append({
                "subject_id": subj.id,
                "subject_name": subj.name,
                "subject_code": subj.code,
                "color": subj.color,
                "total_exams": subj.exams.count(),
                "total_attempts": sub_attempts_count,
                "average": sub_avg
            })

        subject_averages.sort(key=lambda s: s["subject_name"])

        return Response({
            "global_average": global_average,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_attempts": total_attempts,
            "pass_rate": pass_rate,
            "subject_averages": subject_averages
        }, status=status.HTTP_200_OK)
