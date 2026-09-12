"""
Acadivo — Views
Step 4: admin_dashboard, student_list, student_add, student_edit, student_delete — FULL.
All other views remain stubs until their step.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Avg, Count, Q

from .models import (
    Batch, Student, Subject, SemesterElective,
    Marks, SemesterResult, OverallResult
)
from .forms import StudentForm


# ── DECORATORS ────────────────────────────────────────────────

def admin_required(view_func):
    """Redirect non-staff users to dashboard."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Access denied. Admin only.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def student_required(view_func):
    """Redirect staff users away from student pages."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ── AUTH ──────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
            return render(request, 'results/login.html')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('dashboard')
            messages.error(request, 'Your account has been disabled. Contact admin.')
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    return render(request, 'results/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been signed out successfully.')
    return redirect('login')


# ── ROOT DASHBOARD ─────────────────────────────────────────────

@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')
    return redirect('student_dashboard')


# ══════════════════════════════════════════════════════════════
# STEP 4 — ADMIN DASHBOARD + STUDENT MANAGEMENT
# ══════════════════════════════════════════════════════════════

@admin_required
def admin_dashboard(request):
    """
    Admin home: batch-wise stats, top performers, result status.
    """
    batches = Batch.objects.all().prefetch_related('students')

    # Stat cards
    total_students    = Student.objects.filter(is_active=True).count()
    results_published = SemesterResult.objects.filter(is_published=True).count()
    pending_publish   = SemesterResult.objects.filter(is_published=False).count()

    # Avg CGPA for TY batch
    ty_batch = Batch.objects.filter(name='TY').first()
    avg_cgpa = OverallResult.objects.filter(
        student__batch=ty_batch
    ).aggregate(avg=Avg('cgpa'))['avg'] if ty_batch else None
    avg_cgpa = round(float(avg_cgpa), 1) if avg_cgpa else 0

    # Top 5 performers overall (by CGPA)
    top_performers = OverallResult.objects.select_related(
        'student', 'student__batch'
    ).order_by('-cgpa')[:5]

    # Batch result status
    batch_status = []
    for batch in batches:
        sems    = batch.semesters          # e.g. [1,2] for FY
        total   = Student.objects.filter(batch=batch, is_active=True).count()
        pub     = SemesterResult.objects.filter(
                    student__batch=batch, is_published=True
                  ).values('semester').distinct().count()
        batch_status.append({
            'batch':    batch,
            'sems':     sems,
            'total':    total,
            'published': pub,
            'pct':       int((pub / len(sems)) * 100) if sems else 0,
        })

    ctx = {
        'active_nav':       'dashboard',
        'topbar_title':     'Dashboard',
        'topbar_sub':       'Academic Year 2025–26',
        'total_students':   total_students,
        'results_published': results_published,
        'pending_publish':  pending_publish,
        'avg_cgpa':         avg_cgpa,
        'top_performers':   top_performers,
        'batch_status':     batch_status,
    }
    return render(request, 'results/admin_dashboard.html', ctx)


# ── STUDENT LIST ───────────────────────────────────────────────

@admin_required
def student_list(request):
    """
    Shows all students. Filterable by batch, searchable by name/roll.
    """
    batch_filter = request.GET.get('batch', '')
    search       = request.GET.get('q', '').strip()

    students = Student.objects.select_related(
        'batch', 'user', 'overall_result'
    ).filter(is_active=True).order_by('batch__name', 'roll_number')

    if batch_filter:
        students = students.filter(batch__name=batch_filter)
    if search:
        students = students.filter(
            Q(roll_number__icontains=search) |
            Q(full_name__icontains=search) |
            Q(email__icontains=search)
        )

    batches = Batch.objects.all()

    ctx = {
        'active_nav':    'students',
        'topbar_title':  'Students',
        'topbar_sub':    f'{students.count()} students',
        'students':      students,
        'batches':       batches,
        'batch_filter':  batch_filter,
        'search':        search,
    }
    return render(request, 'results/student_list.html', ctx)


# ── STUDENT ADD ────────────────────────────────────────────────

@admin_required
def student_add(request):
    """
    Admin creates a student account.
    Roll number becomes the login username.
    """
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            roll     = form.cleaned_data['roll_number']
            name     = form.cleaned_data['full_name']
            email    = form.cleaned_data['email']
            batch    = form.cleaned_data['batch']
            password = form.cleaned_data['password']

            # Create Django User
            user = User.objects.create_user(
                username=roll,
                email=email,
                password=password,
                first_name=name.split()[0],
                last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                is_staff=False,
                is_superuser=False,
            )

            # Create Student profile
            Student.objects.create(
                user=user,
                roll_number=roll,
                full_name=name,
                email=email,
                phone=form.cleaned_data.get('phone', ''),
                batch=batch,
            )

            messages.success(request, f'Student "{name}" ({roll}) created successfully.')
            return redirect('student_list')
    else:
        form = StudentForm()

    ctx = {
        'active_nav':   'students',
        'topbar_title': 'Add Student',
        'topbar_sub':   'Create a new student account',
        'form':         form,
        'action':       'Add',
    }
    return render(request, 'results/student_form.html', ctx)


# ── STUDENT EDIT ───────────────────────────────────────────────

@admin_required
def student_edit(request, pk):
    """
    Admin edits student details.
    Password field is optional — leave blank to keep existing.
    """
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            name     = form.cleaned_data['full_name']
            email    = form.cleaned_data['email']
            batch    = form.cleaned_data['batch']
            password = form.cleaned_data.get('password', '').strip()

            # Update student
            student.full_name = name
            student.email     = email
            student.phone     = form.cleaned_data.get('phone', '')
            student.batch     = batch
            student.save()

            # Update Django User
            student.user.email      = email
            student.user.first_name = name.split()[0]
            student.user.last_name  = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            if password:
                student.user.set_password(password)
            student.user.save()

            messages.success(request, f'Student "{name}" updated successfully.')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)

    ctx = {
        'active_nav':   'students',
        'topbar_title': 'Edit Student',
        'topbar_sub':   f'{student.full_name} — {student.roll_number}',
        'form':         form,
        'student':      student,
        'action':       'Save Changes',
    }
    return render(request, 'results/student_form.html', ctx)


# ── STUDENT DELETE ─────────────────────────────────────────────

@admin_required
def student_delete(request, pk):
    """Soft-delete: sets is_active=False. POST only."""
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.full_name
        student.is_active = False
        student.save()
        student.user.is_active = False
        student.user.save()
        messages.success(request, f'Student "{name}" has been deactivated.')
    return redirect('student_list')


# ══════════════════════════════════════════════════════════════
# STUBS — Steps 5-11
# ══════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
# STEP 5 — SUBJECT MANAGEMENT + ELECTIVE SELECTOR
# ══════════════════════════════════════════════════════════════

@admin_required
def subject_list(request):
    """
    Lists all subjects grouped by semester.
    Admin can filter by semester and subject type.
    """
    from .models import Subject
    sem_filter  = request.GET.get('sem', '')
    type_filter = request.GET.get('type', '')

    subjects = Subject.objects.all().order_by('semester', 'order')

    if sem_filter:
        subjects = subjects.filter(semester=sem_filter)
    if type_filter:
        subjects = subjects.filter(subject_type=type_filter)

    # Group by semester for display
    from itertools import groupby
    from .models import SEMESTER_CHOICES
    grouped = {}
    for sem_num, sem_label in SEMESTER_CHOICES:
        sem_subjects = subjects.filter(semester=sem_num)
        if sem_subjects.exists() or not sem_filter:
            grouped[sem_num] = {
                'label':     sem_label,
                'subjects':  sem_subjects,
                'total':     sem_subjects.count(),
                'theory':    sem_subjects.filter(subject_type='TH').count(),
                'practical': sem_subjects.filter(subject_type='PR').count(),
            }

    ctx = {
        'active_nav':   'subjects',
        'topbar_title': 'Subjects',
        'topbar_sub':   f'{subjects.count()} subjects across 6 semesters',
        'grouped':      grouped,
        'sem_filter':   sem_filter,
        'type_filter':  type_filter,
        'sem_choices':  [(str(n), l) for n, l in SEMESTER_CHOICES],
    }
    return render(request, 'results/subject_list.html', ctx)


@admin_required
def subject_add(request):
    from .forms import SubjectForm
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{form.cleaned_data["name"]}" added.')
            return redirect('subject_list')
    else:
        form = SubjectForm()
    ctx = {
        'active_nav':   'subjects',
        'topbar_title': 'Add Subject',
        'topbar_sub':   'Add a new subject to the syllabus',
        'form':         form,
        'action':       'Add Subject',
    }
    return render(request, 'results/subject_form.html', ctx)


@admin_required
def subject_edit(request, pk):
    from .models import Subject
    from .forms import SubjectForm
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subject.name}" updated.')
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subject)
    ctx = {
        'active_nav':   'subjects',
        'topbar_title': 'Edit Subject',
        'topbar_sub':   subject.name,
        'form':         form,
        'subject':      subject,
        'action':       'Save Changes',
    }
    return render(request, 'results/subject_form.html', ctx)


@admin_required
def elective_select(request):
    """
    Admin picks ONE elective per batch per semester per elective_group.
    That subject then applies to ALL students of that batch/semester.
    """
    from .models import Subject, SemesterElective, Batch, SEMESTER_CHOICES
    from itertools import groupby

    batches = Batch.objects.all()

    # Find all elective groups that exist
    elective_subjects = Subject.objects.filter(
        is_elective=True, is_active=True
    ).order_by('semester', 'elective_group', 'name')

    # Group by (semester, elective_group)
    elective_slots = {}
    for subj in elective_subjects:
        key = (subj.semester, subj.elective_group)
        if key not in elective_slots:
            elective_slots[key] = []
        elective_slots[key].append(subj)

    if request.method == 'POST':
        batch_id       = request.POST.get('batch')
        semester       = request.POST.get('semester')
        elective_group = request.POST.get('elective_group')
        subject_id     = request.POST.get('subject')

        batch   = get_object_or_404(Batch, pk=batch_id)
        subject = get_object_or_404(Subject, pk=subject_id)

        obj, created = SemesterElective.objects.update_or_create(
            batch=batch,
            semester=semester,
            elective_group=elective_group,
            defaults={
                'selected_subject': subject,
                'set_by':           request.user,
            }
        )
        action = 'set' if created else 'updated'
        messages.success(
            request,
            f'Elective {action}: {subject.name} selected for '
            f'{batch.name} Sem {semester} ({elective_group}).'
        )
        return redirect('elective_select')

    # Current selections — keys: (batch_id int, semester int, elective_group str)
    current = {}
    for sel in SemesterElective.objects.select_related('batch', 'selected_subject', 'set_by'):
        current[(sel.batch_id, int(sel.semester), sel.elective_group)] = sel

    ctx = {
        'active_nav':      'subjects',
        'topbar_title':    'Elective Selection',
        'topbar_sub':      'Choose one elective per group per batch',
        'batches':         batches,
        'elective_slots':  elective_slots,
        'current':         current,
        'sem_choices':     SEMESTER_CHOICES,
    }
    return render(request, 'results/elective_select.html', ctx)

# ══════════════════════════════════════════════════════════════
# STEP 6 — MARK ENTRY + CSV UPLOAD
# ══════════════════════════════════════════════════════════════

@admin_required
def marks_entry(request):
    """
    Admin selects batch + semester + student, then enters
    CE and ESE marks per subject. Grades auto-calculated on save.
    SGPA is recalculated after every save.
    """
    from .models import Subject, SemesterElective, SEMESTER_CHOICES
    from .utils import calculate_sgpa

    batches  = Batch.objects.all()
    students = Student.objects.none()
    subjects = Subject.objects.none()
    selected_student = None
    sem_result       = None
    marks_data       = []

    # Read filter params
    batch_id    = request.GET.get('batch') or request.POST.get('batch')
    semester    = request.GET.get('semester') or request.POST.get('semester')
    student_id  = request.GET.get('student') or request.POST.get('student')

    selected_batch = None
    if batch_id:
        selected_batch = Batch.objects.filter(pk=batch_id).first()

    if selected_batch and semester:
        students = Student.objects.filter(
            batch=selected_batch, is_active=True
        ).order_by('roll_number')

    if selected_batch and semester and student_id:
        selected_student = get_object_or_404(
            Student, pk=student_id, batch=selected_batch, is_active=True
        )

        # Build subject list — non-electives + selected electives for this batch
        non_elective = Subject.objects.filter(
            semester=semester, is_active=True, is_elective=False
        ).order_by('order')

        elected = SemesterElective.objects.filter(
            batch=selected_batch, semester=semester
        ).select_related('selected_subject')
        elective_subjects = [e.selected_subject for e in elected]

        subjects = list(non_elective) + elective_subjects

        # Handle POST — save marks
        if request.method == 'POST' and 'save_marks' in request.POST:
            saved_count  = 0
            error_count  = 0
            error_msgs   = []

            for subj in subjects:
                ce_key  = f'ce_{subj.pk}'
                ese_key = f'ese_{subj.pk}'
                ce_val  = request.POST.get(ce_key, '').strip()
                ese_val = request.POST.get(ese_key, '').strip()

                if not ce_val and not ese_val:
                    continue  # skip blank rows

                try:
                    from decimal import Decimal
                    ce  = Decimal(ce_val)
                    ese = Decimal(ese_val)
                except Exception:
                    error_msgs.append(f'{subj.name}: invalid marks entered.')
                    error_count += 1
                    continue

                if ce < 0 or ce > subj.ce_max:
                    error_msgs.append(f'{subj.name}: CE {ce} out of range (0–{subj.ce_max}).')
                    error_count += 1
                    continue
                if ese < 0 or ese > subj.ese_max:
                    error_msgs.append(f'{subj.name}: ESE {ese} out of range (0–{subj.ese_max}).')
                    error_count += 1
                    continue

                marks_obj, _ = Marks.objects.update_or_create(
                    student=selected_student,
                    subject=subj,
                    semester=int(semester),
                    defaults={
                        'ce_marks':   ce,
                        'ese_marks':  ese,
                        'entered_by': request.user,
                    }
                )
                marks_obj.save()  # triggers grade auto-calc
                saved_count += 1

            # Recalculate SGPA
            if saved_count > 0:
                calculate_sgpa(selected_student, int(semester))
                messages.success(
                    request,
                    f'Marks saved for {selected_student.full_name} '
                    f'({saved_count} subject{"s" if saved_count != 1 else ""}). '
                    f'SGPA recalculated.'
                )
            for msg in error_msgs:
                messages.error(request, msg)

        # Build marks data for template display
        for subj in subjects:
            existing = Marks.objects.filter(
                student=selected_student,
                subject=subj,
                semester=int(semester)
            ).first()
            marks_data.append({
                'subject':  subj,
                'marks':    existing,
                'ce_val':   existing.ce_marks  if existing else '',
                'ese_val':  existing.ese_marks if existing else '',
            })

        # Current SGPA for this semester
        sem_result = SemesterResult.objects.filter(
            student=selected_student, semester=int(semester)
        ).first()

    ctx = {
        'active_nav':       'marks',
        'topbar_title':     'Mark Entry',
        'topbar_sub':       (
            f'{selected_student.full_name} — Sem {semester}'
            if selected_student else 'Select batch, semester and student'
        ),
        'batches':          batches,
        'students':         students,
        'subjects':         subjects,
        'marks_data':       marks_data,
        'sem_choices':      SEMESTER_CHOICES,
        'selected_batch':   selected_batch,
        'selected_semester': semester,
        'selected_student': selected_student,
        'sem_result':       sem_result,
    }
    return render(request, 'results/marks_entry.html', ctx)


@admin_required
def marks_upload(request):
    """
    Bulk CSV upload for marks.
    Supports download of blank CSV template too.
    """
    from .utils import parse_marks_csv, generate_excel_template
    from .models import SEMESTER_CHOICES
    import csv as csv_mod
    from django.http import HttpResponse as HR

    batches = Batch.objects.all()
    upload_result = None

    # Download styled Excel template
    if request.method == 'GET' and request.GET.get('action') == 'template':
        batch_id = request.GET.get('batch')
        semester = request.GET.get('semester')
        if batch_id and semester:
            from .utils import generate_excel_template
            batch = get_object_or_404(Batch, pk=batch_id)
            buffer = generate_excel_template(int(semester), batch)
            filename = (
                f'Acadivo_Marks_Template_{batch.name}_Sem{semester}.xlsx'
            )
            resp = HR(
                buffer.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp

    # Handle CSV upload
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
        elif not csv_file.name.endswith('.csv'):
            messages.error(request, 'Only .csv files are accepted.')
        else:
            upload_result = parse_marks_csv(csv_file, entered_by=request.user)

            # Recalculate SGPA for affected students
            if upload_result['saved'] > 0:
                from .utils import calculate_sgpa
                affected = Marks.objects.filter(
                    entered_by=request.user
                ).values_list('student', 'semester').distinct()
                for student_id, sem in affected:
                    student = Student.objects.filter(pk=student_id).first()
                    if student:
                        calculate_sgpa(student, sem)

            if upload_result['saved']:
                messages.success(
                    request,
                    f'{upload_result["saved"]} mark record(s) saved successfully.'
                )
            if upload_result['errors']:
                messages.warning(
                    request,
                    f'{len(upload_result["errors"])} row(s) had errors — see details below.'
                )

    ctx = {
        'active_nav':    'marks',
        'topbar_title':  'CSV Upload',
        'topbar_sub':    'Bulk upload marks from a spreadsheet',
        'batches':       batches,
        'sem_choices':   SEMESTER_CHOICES,
        'upload_result': upload_result,
    }
    return render(request, 'results/marks_upload.html', ctx)

# ══════════════════════════════════════════════════════════════
# STEP 8 — RESULT PREVIEW + PUBLISH + EMAIL
# ══════════════════════════════════════════════════════════════

@admin_required
def result_preview(request):
    """
    Admin reviews calculated results before publishing.
    Shows SGPA per student, pass/fail, for selected batch + semester.
    """
    from .models import SEMESTER_CHOICES
    batches  = Batch.objects.all()
    batch_id = request.GET.get('batch', '')
    semester = request.GET.get('semester', '')

    selected_batch = None
    preview_data   = []
    total_pass     = 0
    total_fail     = 0

    if batch_id and semester:
        selected_batch = get_object_or_404(Batch, pk=batch_id)
        students = Student.objects.filter(
            batch=selected_batch, is_active=True
        ).order_by('roll_number')

        for student in students:
            sem_result = SemesterResult.objects.filter(
                student=student, semester=int(semester)
            ).first()
            marks_qs = Marks.objects.filter(
                student=student, semester=int(semester)
            ).select_related('subject').order_by('subject__order')

            if sem_result and sem_result.is_pass:
                total_pass += 1
            elif sem_result:
                total_fail += 1

            preview_data.append({
                'student':    student,
                'sem_result': sem_result,
                'marks':      marks_qs,
                'has_marks':  marks_qs.exists(),
            })

    already_published = False
    if selected_batch and semester:
        already_published = SemesterResult.objects.filter(
            student__batch=selected_batch,
            semester=int(semester),
            is_published=True,
        ).exists()

    ctx = {
        'active_nav':        'publish',
        'topbar_title':      'Result Preview',
        'topbar_sub':        'Review before publishing',
        'batches':           batches,
        'sem_choices':       SEMESTER_CHOICES,
        'selected_batch':    selected_batch,
        'selected_semester': semester,
        'preview_data':      preview_data,
        'total_pass':        total_pass,
        'total_fail':        total_fail,
        'already_published': already_published,
    }
    return render(request, 'results/result_preview.html', ctx)


@admin_required
def result_publish(request):
    """
    Admin publishes results for a batch + semester.
    On POST:
      1. Recalculate SGPA for every student in batch
      2. Set SemesterResult.is_published = True
      3. Recalculate CGPA for every student
      4. Send email notification to each student
    """
    from .models import SEMESTER_CHOICES
    from .utils import calculate_sgpa, calculate_cgpa, send_result_email
    import django.utils.timezone as tz

    batches  = Batch.objects.all()
    batch_id = request.POST.get('batch') or request.GET.get('batch', '')
    semester = request.POST.get('semester') or request.GET.get('semester', '')

    if request.method == 'POST' and batch_id and semester:
        selected_batch = get_object_or_404(Batch, pk=batch_id)
        students       = Student.objects.filter(
            batch=selected_batch, is_active=True
        )
        sem_int        = int(semester)
        published_count = 0
        email_count     = 0
        email_errors    = []

        for student in students:
            # 1. Recalculate SGPA
            calculate_sgpa(student, sem_int)

            # 2. Publish
            sem_result = SemesterResult.objects.filter(
                student=student, semester=sem_int
            ).first()

            if sem_result:
                sem_result.is_published  = True
                sem_result.published_at  = tz.now()
                sem_result.published_by  = request.user
                sem_result.save()
                published_count += 1

                # 3. Recalculate CGPA
                calculate_cgpa(student)

                # 4. Send email
                if student.email:
                    sent, err = send_result_email(student, sem_result)
                    if sent:
                        email_count += 1
                    else:
                        email_errors.append(f'{student.roll_number}: {err}')

        messages.success(
            request,
            f'Results published for {selected_batch.get_name_display()} '
            f'Semester {semester} — {published_count} student(s). '
            f'{email_count} email notification(s) sent.'
        )
        if email_errors:
            for err in email_errors:
                messages.warning(request, f'Email error — {err}')

        return redirect(
            f'{request.path}?batch={batch_id}&semester={semester}'
        )

    # GET — show publish form
    selected_batch = None
    publish_ready  = []

    if batch_id and semester:
        selected_batch = get_object_or_404(Batch, pk=batch_id)
        students = Student.objects.filter(
            batch=selected_batch, is_active=True
        ).order_by('roll_number')

        for student in students:
            sem_result = SemesterResult.objects.filter(
                student=student, semester=int(semester)
            ).first()
            marks_count = Marks.objects.filter(
                student=student, semester=int(semester)
            ).count()
            publish_ready.append({
                'student':      student,
                'sem_result':   sem_result,
                'marks_count':  marks_count,
                'can_publish':  sem_result is not None,
                'already_pub':  sem_result.is_published if sem_result else False,
            })


    publish_steps = [
        {'icon': '✓', 'text': 'SGPA is recalculated for every student in this batch'},
        {'icon': '✓', 'text': 'Results become visible to students on the portal immediately'},
        {'icon': '✓', 'text': 'Overall CGPA is updated for each student'},
        {'icon': '✉', 'text': 'Email notification sent to each student who has an email on record'},
    ]

    ctx = {
        'active_nav':        'publish',
        'topbar_title':      'Publish Results',
        'topbar_sub':        'Make results visible to students and send email alerts',
        'batches':           batches,
        'sem_choices':       SEMESTER_CHOICES,
        'selected_batch':    selected_batch,
        'selected_semester': semester,
        'publish_ready':     publish_ready,
        'batch_id':          batch_id,
        'semester':          semester,
        'publish_steps':     publish_steps,
    }
    return render(request, 'results/result_publish.html', ctx)

# ══════════════════════════════════════════════════════════════
# STEP 7 — STUDENT DASHBOARD + RESULTS
# ══════════════════════════════════════════════════════════════

@student_required
def student_dashboard(request):
    """
    Student home — CGPA count-up, latest semester result,
    SGPA trend chart data, published result status per sem.
    """
    student = get_object_or_404(Student, user=request.user, is_active=True)

    # All published semester results ordered by semester
    published_results = SemesterResult.objects.filter(
        student=student, is_published=True
    ).order_by('semester')

    # Overall CGPA
    overall = OverallResult.objects.filter(student=student).first()
    cgpa    = float(overall.cgpa) if overall else 0.0

    # Latest published result
    latest_result = published_results.last()

    # Chart data — SGPA per semester (for Chart.js)
    chart_labels = [f'Sem {r.semester}' for r in published_results]
    chart_data   = [float(r.sgpa) for r in published_results]

    # Marks for latest semester (shown in dashboard table)
    latest_marks = []
    if latest_result:
        latest_marks = Marks.objects.filter(
            student=student,
            semester=latest_result.semester,
        ).select_related('subject').order_by('subject__order')

    # All semesters in student's batch — published status
    batch_sems = student.batch.semesters  # e.g. [1,2] or [5,6]
    sem_status = []
    for sem_num in range(1, 7):
        result = published_results.filter(semester=sem_num).first()
        sem_status.append({
            'num':       sem_num,
            'result':    result,
            'published': result is not None,
            'current':   sem_num in batch_sems,
        })

    ctx = {
        'active_nav':       'dashboard',
        'topbar_title':     'My Dashboard',
        'topbar_sub':       f'{student.batch.get_name_display()} · BSc Computer Science · 2025–26',
        'student':          student,
        'overall':          overall,
        'cgpa':             cgpa,
        'latest_result':    latest_result,
        'latest_marks':     latest_marks,
        'published_results':published_results,
        'chart_labels':     chart_labels,
        'chart_data':       chart_data,
        'sem_status':       sem_status,
        'semesters_done':   published_results.count(),
    }
    return render(request, 'results/student_dashboard.html', ctx)


@student_required
def student_results(request):
    """
    Student views result for a specific semester.
    Defaults to latest published semester.
    """
    student = get_object_or_404(Student, user=request.user, is_active=True)

    sem_param = request.GET.get('sem', '')

    published_results = SemesterResult.objects.filter(
        student=student, is_published=True
    ).order_by('semester')

    if not published_results.exists():
        ctx = {
            'active_nav':    'results',
            'topbar_title':  'My Results',
            'topbar_sub':    'No results published yet',
            'student':       student,
            'no_results':    True,
        }
        return render(request, 'results/student_result.html', ctx)

    # Determine which semester to show
    if sem_param:
        sem_result = published_results.filter(semester=int(sem_param)).first()
        if not sem_result:
            sem_result = published_results.last()
    else:
        sem_result = published_results.last()

    # Marks for this semester
    marks_qs = Marks.objects.filter(
        student=student,
        semester=sem_result.semester,
    ).select_related('subject').order_by('subject__order')

    # Overall CGPA
    overall = OverallResult.objects.filter(student=student).first()

    ctx = {
        'active_nav':         'results',
        'topbar_title':       'My Results',
        'topbar_sub':         f'Semester {sem_result.semester} — {sem_result.get_result_label() if hasattr(sem_result, "get_result_label") else ("PASS" if sem_result.is_pass else "FAIL")}',
        'student':            student,
        'sem_result':         sem_result,
        'marks':              marks_qs,
        'overall':            overall,
        'published_results':  published_results,
        'selected_sem':       sem_result.semester,
        'no_results':         False,
    }
    return render(request, 'results/student_result.html', ctx)


@student_required
def student_history(request):
    """All semesters history — Step 8, implemented here as it reuses student_result data."""
    return redirect('student_results')


# ══════════════════════════════════════════════════════════════
# STEP 9 — PDF MARKSHEET GENERATION
# ══════════════════════════════════════════════════════════════

@student_required
def marksheet_list(request):
    """Student sees all their published semesters with download links."""
    student = get_object_or_404(Student, user=request.user, is_active=True)
    published = SemesterResult.objects.filter(
        student=student, is_published=True
    ).order_by('semester')
    overall = OverallResult.objects.filter(student=student).first()
    ctx = {
        'active_nav':   'marksheet',
        'topbar_title': 'My Marksheets',
        'topbar_sub':   'Download your semester marksheets as PDF',
        'student':      student,
        'published':    published,
        'overall':      overall,
    }
    return render(request, 'results/marksheet_list.html', ctx)


@login_required
def download_marksheet(request, student_id, sem):
    """
    Generate and stream a PDF marksheet.
    Students can only download their own. Admin can download any.
    """
    from .utils import generate_marksheet_pdf
    from django.http import HttpResponse as HR

    if request.user.is_staff:
        student = get_object_or_404(Student, pk=student_id, is_active=True)
    else:
        student = get_object_or_404(Student, user=request.user, is_active=True)
        if student.pk != student_id:
            messages.error(request, 'Access denied.')
            return redirect('student_dashboard')

    # Must be published
    sem_result = SemesterResult.objects.filter(
        student=student, semester=sem, is_published=True
    ).first()
    if not sem_result:
        messages.error(request, 'Result not published yet for this semester.')
        return redirect('student_results')

    try:
        buffer = generate_marksheet_pdf(student, sem)
        filename = (
            f'Marksheet_{student.roll_number}_Sem{sem}_'
            f'{student.batch.name}.pdf'
        )
        response = HR(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f'Could not generate PDF: {e}')
        return redirect('student_results')
