# users/views.py
"""Views for Users app: admin, student, and professor workflows.

Includes:
- Admin: CRUD for users, faculties, careers, subjects, finals, and assignments.
- Student: dashboard, subject/final inscriptions, regular certificate.
- Professor: dashboard, grade management, final inscriptions.

Notes:
    - Access control via role-based predicates (is_admin/is_student/is_professor).
    - Uses messages framework for user feedback.
    - Keeps business rules minimal in views; core rules live in models/services.
"""

from io import BytesIO
from pathlib import Path

from docxtpl import DocxTemplate
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from academics.forms import CareerForm, FacultyForm, FinalExamForm, GradeForm, SubjectForm
from academics.models import Career, Faculty, FinalExam, Grade, Subject
from inscriptions.models import FinalExamInscription, SubjectInscription
from users.forms import AdministratorProfileForm, ProfessorProfileForm, StudentProfileForm, UserForm
from users.models import CustomUser, Professor, Student


# --------- Permisos y Clases Base ---------
def is_admin(user):
    """Return True if the user is authenticated and has administrator role."""
    return user.is_authenticated and user.role == CustomUser.Role.ADMIN


class BaseAdminView:
    """Clase base para vistas de administración que aplica permisos.
    
    Esto cumple con el principio DRY al centralizar la lógica de permisos.
    """

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return user_passes_test(is_admin)(login_required(view))


# --------- Vistas de Admin (refactorizadas) -------
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """
    Render the admin dashboard.
    """
    return render(request, "users/admin_dashboard.html")


class UserListView(BaseAdminView, ListView):
    """Lista todos los usuarios."""
    model = CustomUser
    template_name = "users/user_list.html"
    context_object_name = "users"


class UserCreateView(BaseAdminView, CreateView):
    """Crea un nuevo usuario y su perfil asociado."""
    model = CustomUser
    form_class = UserForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["user_form"] = UserForm(self.request.POST)
            context["student_profile_form"] = StudentProfileForm(self.request.POST)
            context["professor_profile_form"] = ProfessorProfileForm(self.request.POST)
            context["administrator_profile_form"] = AdministratorProfileForm(self.request.POST)
            context["selected_role"] = self.request.POST.get("role")
        else:
            context["user_form"] = UserForm()
            context["student_profile_form"] = StudentProfileForm()
            context["professor_profile_form"] = ProfessorProfileForm()
            context["administrator_profile_form"] = AdministratorProfileForm()
            context["selected_role"] = None
        return context

    def form_valid(self, user_form):
        selected_role = self.request.POST.get("role")
        profile_form = None
        if selected_role == CustomUser.Role.STUDENT:
            profile_form = StudentProfileForm(self.request.POST)
        elif selected_role == CustomUser.Role.PROFESSOR:
            profile_form = ProfessorProfileForm(self.request.POST)
        elif selected_role == CustomUser.Role.ADMIN:
            profile_form = AdministratorProfileForm(self.request.POST)

        if profile_form is None or profile_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                if profile_form:
                    profile = profile_form.save(commit=False)
                    profile.user = user
                    profile.save()
            messages.success(self.request, "Usuario creado correctamente.")
            return redirect(self.success_url)
        return self.form_invalid(user_form)


class UserUpdateView(BaseAdminView, UpdateView):
    """Actualiza un usuario y su perfil asociado."""
    model = CustomUser
    form_class = UserForm
    template_name = "users/user_form.html"
    success_url = reverse_lazy("users:user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        if self.request.POST:
            posted_role = self.request.POST.get("role")
            context["student_profile_form"] = StudentProfileForm(self.request.POST, instance=getattr(user, "student", None))
            context["professor_profile_form"] = ProfessorProfileForm(self.request.POST, instance=getattr(user, "professor", None))
            context["administrator_profile_form"] = AdministratorProfileForm(self.request.POST, instance=getattr(user, "administrator", None))
            context["selected_role"] = posted_role
        else:
            context["user_form"] = UserForm(instance=user)
            context["student_profile_form"] = StudentProfileForm(instance=getattr(user, "student", None))
            context["professor_profile_form"] = ProfessorProfileForm(instance=getattr(user, "professor", None))
            context["administrator_profile_form"] = AdministratorProfileForm(instance=getattr(user, "administrator", None))
            context["selected_role"] = user.role
        return context

    def form_valid(self, form):
        user = self.get_object()
        role = form.cleaned_data["role"]

        if role != user.role:
            if getattr(user, "student", None):
                user.student.delete()
            if getattr(user, "professor", None):
                user.professor.delete()
            if getattr(user, "administrator", None):
                user.administrator.delete()
            messages.info(self.request, "El perfil anterior ha sido eliminado debido al cambio de rol.")

        with transaction.atomic():
            user = form.save()
            profile_form = None
            if role == CustomUser.Role.STUDENT:
                profile_form = StudentProfileForm(self.request.POST)
            elif role == CustomUser.Role.PROFESSOR:
                profile_form = ProfessorProfileForm(self.request.POST)
            elif role == CustomUser.Role.ADMIN:
                profile_form = AdministratorProfileForm(self.request.POST)

            if profile_form:
                if profile_form.is_valid():
                    profile = profile_form.save(commit=False)
                    profile.user = user
                    profile.save()
                else:
                    return self.form_invalid(form)

        messages.success(self.request, "Usuario actualizado correctamente.")
        return redirect(self.success_url)


class UserDeleteView(BaseAdminView, DeleteView):
    """Elimina un usuario después de la confirmación."""
    model = CustomUser
    template_name = "users/confirm_delete.html"
    success_url = reverse_lazy("users:user-list")
    context_object_name = "user"


# Vistas CRUD para los modelos Académicos
class FacultyListView(BaseAdminView, ListView):
    model = Faculty
    template_name = "users/faculty_list.html"
    context_object_name = "faculties"


class FacultyCreateView(BaseAdminView, CreateView):
    model = Faculty
    form_class = FacultyForm
    template_name = "users/faculty_form.html"
    success_url = reverse_lazy("users:faculty-list")


class FacultyUpdateView(BaseAdminView, UpdateView):
    model = Faculty
    form_class = FacultyForm
    template_name = "users/faculty_form.html"
    success_url = reverse_lazy("users:faculty-list")
    slug_field = "code"
    slug_url_kwarg = "code"


class FacultyDeleteView(BaseAdminView, DeleteView):
    model = Faculty
    template_name = "users/confirm_delete.html"
    success_url = reverse_lazy("users:faculty-list")
    context_object_name = "object"
    slug_field = "code"
    slug_url_kwarg = "code"


class CareerListView(BaseAdminView, ListView):
    model = Career
    template_name = "users/career_list.html"
    context_object_name = "careers"


class CareerCreateView(BaseAdminView, CreateView):
    model = Career
    form_class = CareerForm
    template_name = "users/career_form.html"
    success_url = reverse_lazy("users:career-list")


class CareerUpdateView(BaseAdminView, UpdateView):
    model = Career
    form_class = CareerForm
    template_name = "users/career_form.html"
    success_url = reverse_lazy("users:career-list")
    slug_field = "code"
    slug_url_kwarg = "code"


class CareerDeleteView(BaseAdminView, DeleteView):
    model = Career
    template_name = "users/confirm_delete.html"
    success_url = reverse_lazy("users:career-list")
    context_object_name = "object"
    slug_field = "code"
    slug_url_kwarg = "code"


class SubjectListView(BaseAdminView, ListView):
    model = Subject
    template_name = "users/subject_list.html"
    context_object_name = "subjects"
    queryset = Subject.objects.select_related("career").all()


class SubjectCreateView(BaseAdminView, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = "users/subject_form.html"
    success_url = reverse_lazy("users:subject-list")


class SubjectUpdateView(BaseAdminView, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = "users/subject_form.html"
    success_url = reverse_lazy("users:subject-list")
    slug_field = "code"
    slug_url_kwarg = "code"


class SubjectDeleteView(BaseAdminView, DeleteView):
    model = Subject
    template_name = "users/confirm_delete.html"
    success_url = reverse_lazy("users:subject-list")
    context_object_name = "object"
    slug_field = "code"
    slug_url_kwarg = "code"


@login_required
@user_passes_test(is_admin)
def assign_subject_professors(request, code):
    """
    Assign/remove professors for a subject.
    """
    subject = get_object_or_404(Subject, code=code)
    if request.method == "POST":
        selected_ids = set(request.POST.getlist("professors"))
        current_ids = set(subject.professors.values_list("pk", flat=True))

        to_add = selected_ids - current_ids
        to_remove = current_ids - selected_ids

        if to_add or to_remove:
            with transaction.atomic():
                if to_add:
                    subject.professors.add(*to_add)
                if to_remove:
                    subject.professors.remove(*to_remove)
            messages.success(request, "Asignaciones actualizadas correctamente.")
        else:
            messages.info(request, "No hubo cambios en las asignaciones.")
        return redirect("users:subject-list")

    profs = Professor.objects.select_related("user").all()
    return render(request, "users/assign_professors.html", {"subject": subject, "professors": profs})


class FinalExamListView(BaseAdminView, ListView):
    model = FinalExam
    template_name = "users/final_list.html"
    context_object_name = "finals"
    queryset = FinalExam.objects.select_related("subject").all()


class FinalExamCreateView(BaseAdminView, CreateView):
    model = FinalExam
    form_class = FinalExamForm
    template_name = "users/final_form.html"
    success_url = reverse_lazy("users:final-list")


class FinalExamUpdateView(BaseAdminView, UpdateView):
    model = FinalExam
    form_class = FinalExamForm
    template_name = "users/final_form.html"
    success_url = reverse_lazy("users:final-list")


class FinalExamDeleteView(BaseAdminView, DeleteView):
    model = FinalExam
    template_name = "users/confirm_delete.html"
    success_url = reverse_lazy("users:final-list")
    context_object_name = "object"


@login_required
@user_passes_test(is_admin)
def assign_final_professors(request, pk):
    """
    Assign/remove professors for a final exam.
    """
    final = get_object_or_404(FinalExam, pk=pk)
    if request.method == "POST":
        selected_ids = set(request.POST.getlist("professors"))
        current_ids = set(final.professors.values_list("pk", flat=True))

        to_add = selected_ids - current_ids
        to_remove = current_ids - selected_ids

        if to_add or to_remove:
            with transaction.atomic():
                if to_add:
                    final.professors.add(*to_add)
                if to_remove:
                    final.professors.remove(*to_remove)
            messages.success(request, "Asignaciones del final actualizadas correctamente.")
        else:
            messages.info(request, "No hubo cambios en las asignaciones.")
        return redirect("users:final-list")

    profs = Professor.objects.select_related("user").all()
    return render(request, "users/assign_professors.html", {"final": final, "professors": profs})


# ------- Vistas de Estudiantes -------
def is_student(user):
    """Return True if the user is authenticated and has student role."""
    return user.is_authenticated and user.role == CustomUser.Role.STUDENT


@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    """
    Render student dashboard with subjects, grades, and inscriptions.
    """
    student = getattr(request.user, "student", None)
    if not student:
        messages.error(request, "Tu perfil de estudiante no está configurado. Contactá a un administrador.")
        return redirect("home")
    subjects = Subject.objects.filter(career=student.career)
    inscriptions = SubjectInscription.objects.filter(student=student).select_related("subject")
    inscribed_subject_codes = list(inscriptions.values_list("subject__code", flat=True))
    grades = Grade.objects.filter(student=student).select_related("subject")

    eligible_subject_ids = (
        grades.filter(status=Grade.StatusSubject.REGULAR)
        .values_list("subject_id", flat=True)
        .distinct()
    )
    eligible_finals = FinalExam.objects.filter(subject_id__in=eligible_subject_ids)

    final_inscriptions = (
        FinalExamInscription.objects.filter(student=student)
        .select_related("final_exam__subject")
        .order_by("final_exam__date")
    )
    inscribed_final_ids = list(final_inscriptions.values_list("final_exam_id", flat=True))

    return render(request, "users/student_dashboard.html", {
        "subjects": subjects,
        "inscriptions": inscriptions,
        "grades": grades,
        "eligible_finals": eligible_finals,
        "final_inscriptions": final_inscriptions,
        "inscribed_final_ids": inscribed_final_ids,
        "inscribed_subject_codes": inscribed_subject_codes})


@login_required
@user_passes_test(is_student)
def subject_inscribe(request, subject_code):
    """
    Create subject inscription and ensure grade record exists.
    """
    student = request.user.student
    subject = get_object_or_404(Subject, code=subject_code, career=student.career)
    if request.method == "POST":
        created = False
        obj, created = SubjectInscription.objects.get_or_create(student=student, subject=subject)
        Grade.objects.get_or_create(student=student, subject=subject)
        if created:
            messages.success(request, "Inscripción a la materia realizada.")
        else:
            messages.info(request, "Ya estabas inscripto en esta materia.")
        return redirect("users:student-dashboard")
    return render(request, "users/inscribe_confirm.html", {"subject": subject})


@login_required
@user_passes_test(is_student)
def final_exam_inscribe(request, final_exam_id):
    """
    Create final exam inscription if the subject status is REGULAR.
    """
    student = request.user.student
    final_exam = get_object_or_404(FinalExam, pk=final_exam_id, subject__career=student.career)
    grade = Grade.objects.filter(student=student, subject=final_exam.subject).order_by("-id").first()
    if not grade or grade.status not in [Grade.StatusSubject.REGULAR]:
        messages.error(request, "Solo puedes inscribirte si la materia está regular.")
        return redirect("users:student-dashboard")
    if request.method == "POST":
        FinalExamInscription.objects.get_or_create(student=student, final_exam=final_exam)
        messages.success(request, "Inscripción al final realizada.")
        return redirect("users:student-dashboard")
    return render(request, "users/inscribe_confirm.html", {"final_exam": final_exam})


@login_required
@user_passes_test(is_student)
def download_regular_certificate(request):
    """
    Generate and download a 'regular student' certificate as DOCX.
    """
    # Evitar acceder a request.user.student directamente (puede lanzar RelatedObjectDoesNotExist)
    user = request.user
    student = Student.objects.filter(user=user).select_related("career__faculty").first()
    if not student:
        messages.error(request, "Tu perfil de estudiante no está configurado. Contactá a un administrador.")
        return redirect("home")

    template_path = Path(settings.BASE_DIR) / "regular_certificate.docx"
    if not template_path.exists():
        messages.error(request, "No se encontró la plantilla de certificado.")
        return redirect("users:student-dashboard")

    today = timezone.localdate()
    context = {
        "full_name": request.user.get_full_name() or request.user.username,
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "dni": request.user.dni,
        "student_id": student.student_id,
        "career_name": student.career.name if student.career else "",
        "career_code": student.career.code if student.career else "",
        "faculty_name": (
            student.career.faculty.name
            if getattr(student, "career", None) and student.career and student.career.faculty
            else ""
        ),
        "enrollment_date": student.enrollment_date.strftime("%d/%m/%Y") if student.enrollment_date else "",
        "today_date": today.strftime("%d/%m/%Y"),
        "today_day": f"{today.day:02d}",
        "today_month": f"{today.month:02d}",
        "today_year": f"{today.year}",
    }

    try:
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        output = BytesIO()
        doc.save(output)
        output.seek(0)
    except Exception:
        messages.error(request, "Ocurrió un error al generar el certificado.")
        return redirect("users:student-dashboard")

    filename = f"certificado-regular-{request.user.last_name or request.user.username}-{today.strftime('%Y%m%d')}.docx"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
    return response


# ------- Vistas de Profesor -------
def is_professor(user):
    """Return True if the user is authenticated and has professor role."""
    return user.is_authenticated and user.role == CustomUser.Role.PROFESSOR


@login_required
@user_passes_test(is_professor)
def professor_dashboard(request):
    """
    Render professor dashboard with assigned subjects and finals.
    """
    professor = getattr(request.user, "professor", None)
    if not professor:
        messages.error(request, "Tu perfil de profesor no está configurado. Contactá a un administrador.")
        return redirect("home")
    subjects = professor.subjects.all()
    finals = professor.final_exams.select_related("subject").all()
    return render(request, "users/professor_dashboard.html", {"subjects": subjects, "finals": finals})


@login_required
@user_passes_test(is_professor)
def grade_list(request, subject_code):
    """
    List grades for a subject and backfill missing Grade entries.
    """
    professor = request.user.professor
    subject = get_object_or_404(Subject, code=subject_code, professors=professor)
    enrolled_student_ids = set(SubjectInscription.objects.filter(subject=subject).values_list("student_id", flat=True))
    existing_grade_student_ids = set(Grade.objects.filter(subject=subject).values_list("student_id", flat=True))
    missing_ids = enrolled_student_ids - existing_grade_student_ids
    if missing_ids:
        Grade.objects.bulk_create([Grade(student_id=sid, subject=subject) for sid in missing_ids])

    grades = (
        Grade.objects.filter(subject=subject)
        .select_related("student__user")
        .order_by("student__user__last_name", "student__user__first_name")
    )
    return render(request, "users/grade_list.html", {"grades": grades, "subject": subject})


@login_required
@user_passes_test(is_professor)
def grade_edit(request, pk):
    """
    Edit a grade record for a student in a professor's subject.
    """
    grade = get_object_or_404(Grade, pk=pk)
    if grade.subject not in request.user.professor.subjects.all():
        messages.error(request, "No puede editar notas de materias no asignadas.")
        return redirect("users:professor-dashboard")
    if not SubjectInscription.objects.filter(student=grade.student, subject=grade.subject).exists():
        messages.error(request, "Solo puede calificar a estudiantes inscriptos en la materia.")
        return redirect("users:grade-list", subject_code=grade.subject.code)

    if request.method == "POST":
        form = GradeForm(request.POST, instance=grade)
        if form.is_valid():
            status_was_changed = "status" in form.changed_data
            saved = form.save()
            if not status_was_changed:
                saved.update_status()
            return redirect("users:grade-list", subject_code=grade.subject.code)
    else:
        form = GradeForm(instance=grade)
    return render(request, "users/grade_form.html", {"form": form, "grade": grade})


@login_required
@user_passes_test(is_professor)
def professor_final_inscriptions(request, final_exam_id):
    """
    List final exam inscriptions assigned to the professor.
    """
    professor = request.user.professor
    final_exam = get_object_or_404(FinalExam, id=final_exam_id, professors=professor)
    inscriptions = (
        FinalExamInscription.objects.filter(final_exam=final_exam)
        .select_related("student__user")
        .order_by("student__user__last_name", "student__user__first_name")
    )
    return render(request, "users/professor_final_inscriptions.html", {
        "final_exam": final_exam, "inscriptions": inscriptions})


import json
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.views import View

from users.services import StudentFileService # Importa el nuevo servicio
from users.models import CustomUser, Student # Asegúrate de que Student esté importado


# ... (resto del código de views.py) ...


# --------- Vistas para la Ficha del Alumno (SOLID) ---------
class StudentFileDocxView(View):
    """
    Vista para generar la Ficha del Alumno en formato DOCX.
    
    Responsabilidad única: generar el archivo Word a partir de los datos.
    """
    def get(self, request, student_id):
        student_data = StudentFileService.get_student_file_data(student_id)
        if not student_data:
            messages.error(request, "Ficha de Alumno no encontrada.")
            return redirect('users:student-dashboard')

        doc_path = Path(settings.BASE_DIR) /"ficha_alumno.docx"
        if not doc_path.exists():
            messages.error(request, "No se encontró la plantilla de la Ficha del Alumno.")
            return redirect('users:student-dashboard')

        try:
            doc = DocxTemplate(str(doc_path))
            doc.render(student_data)
            output = BytesIO()
            doc.save(output)
            output.seek(0)
            
            filename = f"ficha_alumno_{student_id}.docx"
            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        
        except Exception as e:
            messages.error(request, f"Ocurrió un error al generar la Ficha: {e}")
            return redirect('users:student-dashboard')


class StudentFileJSONView(View):
    
    def get(self, request, student_id):
        student_data = StudentFileService.get_student_file_data(student_id)
        if not student_data:
            return JsonResponse({'error': 'Ficha de Alumno no encontrada.'}, status=404)
        return JsonResponse(student_data)