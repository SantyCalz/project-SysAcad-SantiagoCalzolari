"""URL patterns for the Users app.

Sections:
- Admin: CRUD for users, faculties, careers, subjects, finals, and assignments.
- Student: dashboard, subject/final inscriptions, certificates, student file.
- Professor: dashboard, grade management, final inscriptions.

Notes:
    Namespaced via app_name = "users" to enable reverse('users:<name>').
    Access control is enforced in views (role-based decorators or checks).
"""

from django.urls import path

from .views import (
    # Vistas de Admin
    admin_dashboard,
    UserListView, UserCreateView, UserUpdateView, UserDeleteView,
    FacultyListView, FacultyCreateView, FacultyUpdateView, FacultyDeleteView,
    CareerListView, CareerCreateView, CareerUpdateView, CareerDeleteView,
    SubjectListView, SubjectCreateView, SubjectUpdateView, SubjectDeleteView,
    FinalExamListView, FinalExamCreateView, FinalExamUpdateView, FinalExamDeleteView,
    assign_subject_professors,
    assign_final_professors,

    # Vistas de Estudiante
    student_dashboard,
    subject_inscribe,
    final_exam_inscribe,
    download_regular_certificate,
    StudentFileDocxView, # Agregado
    StudentFileJSONView, # Agregado

    # Vistas de Profesor
    professor_dashboard,
    grade_list,
    grade_edit,
    professor_final_inscriptions,
)

app_name = "users"

urlpatterns = [
    # Admin
    path('admin/dashboard/', admin_dashboard, name='admin-dashboard'),
    path('admin/users/', UserListView.as_view(), name='user-list'),
    path('admin/users/create/', UserCreateView.as_view(), name='user-create'),
    path('admin/users/<int:pk>/edit/', UserUpdateView.as_view(), name='user-edit'),
    path('admin/users/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),

    path('admin/faculties/', FacultyListView.as_view(), name='faculty-list'),
    path('admin/faculties/create/', FacultyCreateView.as_view(), name='faculty-create'),
    path('admin/faculties/<str:code>/edit/', FacultyUpdateView.as_view(), name='faculty-edit'),
    path('admin/faculties/<str:code>/delete/', FacultyDeleteView.as_view(), name='faculty-delete'),

    path('admin/careers/', CareerListView.as_view(), name='career-list'),
    path('admin/careers/create/', CareerCreateView.as_view(), name='career-create'),
    path('admin/careers/<str:code>/edit/', CareerUpdateView.as_view(), name='career-edit'),
    path('admin/careers/<str:code>/delete/', CareerDeleteView.as_view(), name='career-delete'),

    path('admin/subjects/', SubjectListView.as_view(), name='subject-list'),
    path('admin/subjects/create/', SubjectCreateView.as_view(), name='subject-create'),
    path('admin/subjects/<str:code>/edit/', SubjectUpdateView.as_view(), name='subject-edit'),
    path('admin/subjects/<str:code>/delete/', SubjectDeleteView.as_view(), name='subject-delete'),
    path('admin/subjects/<str:code>/assign-professors/', assign_subject_professors, name='assign-subject-professors'),

    path('admin/finals/', FinalExamListView.as_view(), name='final-list'),
    path('admin/finals/create/', FinalExamCreateView.as_view(), name='final-create'),
    path('admin/finals/<int:pk>/edit/', FinalExamUpdateView.as_view(), name='final-edit'),
    path('admin/finals/<int:pk>/delete/', FinalExamDeleteView.as_view(), name='final-delete'),
    path('admin/finals/<int:pk>/assign-professors/', assign_final_professors, name='assign-final-professors'),

    # Student
    path('student/dashboard/', student_dashboard, name='student-dashboard'),
    path('student/subject/<str:subject_code>/inscribe/', subject_inscribe, name='subject-inscribe'),
    path('student/final/<int:final_exam_id>/inscribe/', final_exam_inscribe, name='final-inscribe'),
    path('student/certificate/regular/', download_regular_certificate, name='student-regular-certificate'),
    
    # Nuevas rutas para la Ficha del Alumno
    path('student/<str:student_id>/file/docx/', StudentFileDocxView.as_view(), name='student-file-docx'),
    path('student/<str:student_id>/file/json/', StudentFileJSONView.as_view(), name='student-file-json'),

    # Professor
    path('professor/dashboard/', professor_dashboard, name='professor-dashboard'),
    path('professor/grades/<str:subject_code>/', grade_list, name='grade-list'),
    path('professor/grade/<int:pk>/edit/', grade_edit, name='grade-edit'),
    path('professor/final/<int:final_exam_id>/inscriptions/', professor_final_inscriptions, name='professor-final-inscriptions')
]