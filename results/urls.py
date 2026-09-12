"""
Acadivo — Results App URL Configuration
Routes expand each step. All URLs defined upfront so templates
can use {% url 'name' %} without errors.
"""

from django.urls import path
from . import views

urlpatterns = [

    # ── AUTH ──────────────────────────────────────────────
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── DASHBOARD ─────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard,   name='admin_dashboard'),
    path('my/',              views.student_dashboard, name='student_dashboard'),

    # ── ADMIN: STUDENTS ───────────────────────────────────
    path('students/',           views.student_list,   name='student_list'),
    path('students/add/',       views.student_add,    name='student_add'),
    path('students/<int:pk>/edit/',   views.student_edit,   name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),

    # ── ADMIN: SUBJECTS ───────────────────────────────────
    path('subjects/',              views.subject_list,    name='subject_list'),
    path('subjects/add/',          views.subject_add,     name='subject_add'),
    path('subjects/<int:pk>/edit/',views.subject_edit,    name='subject_edit'),
    path('elective/select/',       views.elective_select, name='elective_select'),

    # ── ADMIN: MARKS ──────────────────────────────────────
    path('marks/',         views.marks_entry,  name='marks_entry'),
    path('marks/upload/',  views.marks_upload, name='marks_upload'),

    # ── ADMIN: RESULTS ────────────────────────────────────
    path('results/preview/', views.result_preview, name='result_preview'),
    path('results/publish/', views.result_publish, name='result_publish'),

    # ── STUDENT PORTAL ────────────────────────────────────
    path('my/results/',    views.student_results,  name='student_results'),
    path('my/history/',    views.student_history,  name='student_history'),
    path('my/marksheets/', views.marksheet_list,   name='marksheet_list'),

    # ── PDF DOWNLOAD ──────────────────────────────────────
    path('marksheet/<int:student_id>/<int:sem>/',
         views.download_marksheet, name='download_marksheet'),
]
