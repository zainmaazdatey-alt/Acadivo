"""
Acadivo — Django Admin Registrations
All 7 models registered with proper search, filters, and inline displays.
Access at: /admin/ (superuser login)
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Batch, Student, Subject, SemesterElective,
    Marks, SemesterResult, OverallResult
)


# ── BATCH ──────────────────────────────────────────────────

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display  = ('name', 'get_full_name', 'academic_year', 'student_count', 'sems_label')
    list_filter   = ('academic_year',)
    search_fields = ('name', 'academic_year')

    def get_full_name(self, obj):
        return obj.get_name_display()
    get_full_name.short_description = 'Full Name'

    def sems_label(self, obj):
        s = obj.semesters
        return f'Sem {s[0]} & {s[1]}' if s else '—'
    sems_label.short_description = 'Semesters'


# ── STUDENT ────────────────────────────────────────────────

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display    = ('roll_number', 'full_name', 'batch', 'email', 'cgpa_col', 'is_active')
    list_filter     = ('batch', 'is_active', 'batch__academic_year')
    search_fields   = ('roll_number', 'full_name', 'email')
    ordering        = ('roll_number',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Account',       {'fields': ('user', 'roll_number', 'batch', 'is_active')}),
        ('Personal Info', {'fields': ('full_name', 'email', 'phone')}),
        ('Timestamps',    {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def cgpa_col(self, obj):
        cgpa = obj.current_cgpa
        if cgpa is None:
            return '—'
        c = '#34D399' if float(cgpa) >= 7 else '#FBBF24' if float(cgpa) >= 5 else '#F87171'
        return format_html('<strong style="color:{}">{}</strong>', c, cgpa)
    cgpa_col.short_description = 'CGPA'


# ── SUBJECT ────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ('semester', 'code', 'name', 'subject_type', 'group',
                     'credits', 'ce_max', 'ese_max', 'is_elective', 'order', 'is_active')
    list_filter   = ('semester', 'subject_type', 'group', 'is_elective', 'is_active')
    search_fields = ('name', 'code')
    ordering      = ('semester', 'order')
    list_editable = ('is_active', 'order')
    fieldsets = (
        ('Basic Info',        {'fields': ('semester', 'code', 'name', 'subject_type', 'group', 'credits', 'order')}),
        ('Marks',             {'fields': ('ce_max', 'ese_max')}),
        ('Elective Settings', {'fields': ('is_elective', 'elective_group')}),
        ('Status',            {'fields': ('is_active',)}),
    )


# ── SEMESTER ELECTIVE ──────────────────────────────────────

@admin.register(SemesterElective)
class SemesterElectiveAdmin(admin.ModelAdmin):
    list_display  = ('batch', 'semester', 'elective_group', 'selected_subject', 'set_by', 'set_at')
    list_filter   = ('batch', 'semester', 'elective_group')
    search_fields = ('selected_subject__name', 'elective_group')
    readonly_fields = ('set_at',)


# ── MARKS ──────────────────────────────────────────────────

class MarksInline(admin.TabularInline):
    model   = Marks
    extra   = 0
    fields  = ('subject', 'ce_marks', 'ese_marks', 'total_marks', 'percentage', 'grade', 'is_pass')
    readonly_fields = ('total_marks', 'percentage', 'grade', 'is_pass')


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display    = ('student', 'semester', 'subject', 'ce_marks', 'ese_marks',
                       'total_marks', 'percentage', 'grade_col', 'is_pass')
    list_filter     = ('semester', 'grade', 'is_pass', 'student__batch')
    search_fields   = ('student__roll_number', 'student__full_name', 'subject__name')
    readonly_fields = ('total_marks', 'percentage', 'grade', 'grade_points',
                       'is_pass', 'entered_at', 'updated_at')
    ordering = ('semester', 'student__roll_number')
    fieldsets = (
        ('Student & Subject',          {'fields': ('student', 'subject', 'semester')}),
        ('Marks Entry',                {'fields': ('ce_marks', 'ese_marks')}),
        ('Auto-Calculated (readonly)', {'fields': ('total_marks', 'percentage', 'grade', 'grade_points', 'is_pass'), 'classes': ('collapse',)}),
        ('Meta',                       {'fields': ('entered_by', 'entered_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def grade_col(self, obj):
        colors = {'O':'#34D399','A+':'#BFA3FF','A':'#93C5FD',
                  'B+':'#D8B4FE','B':'#FCD34D','C':'#FDBA74','F':'#F87171'}
        return format_html('<strong style="color:{}">{}</strong>',
                           colors.get(obj.grade, '#fff'), obj.grade)
    grade_col.short_description = 'Grade'


# ── SEMESTER RESULT ────────────────────────────────────────

@admin.register(SemesterResult)
class SemesterResultAdmin(admin.ModelAdmin):
    list_display    = ('student', 'semester', 'sgpa_col', 'total_credits_earned',
                       'total_credits', 'is_pass', 'is_published', 'published_at')
    list_filter     = ('semester', 'is_pass', 'is_published', 'student__batch')
    search_fields   = ('student__roll_number', 'student__full_name')
    readonly_fields = ('sgpa', 'total_credits', 'total_credits_earned',
                       'is_pass', 'calculated_at', 'published_at')
    ordering = ('semester', 'student__roll_number')
    fieldsets = (
        ('Student & Semester',        {'fields': ('student', 'semester')}),
        ('Calculated Results',         {'fields': ('sgpa', 'total_credits', 'total_credits_earned', 'is_pass', 'calculated_at')}),
        ('Publish Controls',           {'fields': ('is_published', 'published_at', 'published_by')}),
    )

    def sgpa_col(self, obj):
        c = '#34D399' if float(obj.sgpa) >= 7 else '#FBBF24' if float(obj.sgpa) >= 5 else '#F87171'
        return format_html('<strong style="color:{}">{}</strong>', c, obj.sgpa)
    sgpa_col.short_description = 'SGPA'


# ── OVERALL RESULT (CGPA) ──────────────────────────────────

@admin.register(OverallResult)
class OverallResultAdmin(admin.ModelAdmin):
    list_display    = ('student', 'cgpa_col', 'semesters_completed', 'standing_col', 'last_updated')
    list_filter     = ('semesters_completed',)
    search_fields   = ('student__roll_number', 'student__full_name')
    readonly_fields = ('cgpa', 'semesters_completed', 'last_updated')

    def cgpa_col(self, obj):
        c = '#34D399' if float(obj.cgpa) >= 7 else '#FBBF24' if float(obj.cgpa) >= 5 else '#F87171'
        return format_html('<strong style="color:{}">{}</strong>', c, obj.cgpa)
    cgpa_col.short_description = 'CGPA'

    def standing_col(self, obj):
        return obj.standing
    standing_col.short_description = 'Standing'
