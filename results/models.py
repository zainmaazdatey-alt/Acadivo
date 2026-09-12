"""
Acadivo — Database Models
Step 2: All 7 tables defined here in one file.
Never touch models after this step — changing models
means new migrations which can break things.

Tables:
  Batch            — FY / SY / TY year groups
  Student          — student account + roll number
  Subject          — NEP BSc CS subjects per semester
  SemesterElective — which elective admin selected for a batch+sem
  Marks            — CE + ESE marks per student per subject
  SemesterResult   — SGPA per student per semester (auto-calculated)
  OverallResult    — CGPA per student (auto-calculated)
"""

import re
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

BATCH_CHOICES = [
    ('FY', 'FY — First Year'),
    ('SY', 'SY — Second Year'),
    ('TY', 'TY — Third Year'),
]

SEMESTER_CHOICES = [
    (1, 'Semester I'),
    (2, 'Semester II'),
    (3, 'Semester III'),
    (4, 'Semester IV'),
    (5, 'Semester V'),
    (6, 'Semester VI'),
]

SUBJECT_TYPE_CHOICES = [
    ('TH', 'Theory'),
    ('PR', 'Practical'),
]

SUBJECT_GROUP_CHOICES = [
    ('Major',     'Major'),
    ('Minor',     'Minor'),
    ('OE',        'Open Elective'),
    ('VSC',       'Value Added / Skill'),
    ('VSEC',      'Value Added / Skill (Elective)'),
    ('AEC',       'Ability Enhancement'),
    ('VEC',       'Value & Ethics'),
    ('IKS',       'Indian Knowledge System'),
    ('CC',        'Co-curricular'),
    ('SEC',       'Skill Enhancement'),
    ('FP',        'Field Project'),
    ('CEP',       'Community Engagement'),
    ('Mandatory', 'Mandatory'),
    ('Elective',  'Elective'),
    ('OJT',       'On Job Training'),
]

GRADE_CHOICES = [
    ('O',  'O — Outstanding'),
    ('A+', 'A+ — Excellent'),
    ('A',  'A — Very Good'),
    ('B+', 'B+ — Good'),
    ('B',  'B — Above Average'),
    ('C',  'C — Average / Pass'),
    ('F',  'F — Fail'),
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def validate_roll_number(value):
    """Roll number must be 7 digits: 4-digit year + 3-digit serial. e.g. 2026001"""
    if not re.match(r'^\d{4}\d{3}$', str(value)):
        raise ValidationError(
            f'"{value}" is not a valid roll number. '
            'Format: 4-digit year + 3-digit serial (e.g. 2026001).'
        )


def compute_grade(percentage):
    """
    Returns (grade_letter, grade_points) from percentage.
    NEP Mumbai University 10-point scale.
    """
    scale = getattr(settings, 'GRADE_SCALE', [
        (90,  'O',  10, 'Outstanding'),
        (75,  'A+',  9, 'Excellent'),
        (65,  'A',   8, 'Very Good'),
        (55,  'B+',  7, 'Good'),
        (50,  'B',   6, 'Above Average'),
        (40,  'C',   5, 'Average / Pass'),
        (0,   'F',   0, 'Fail'),
    ])
    for min_pct, grade, gp, _ in scale:
        if percentage >= min_pct:
            return grade, gp
    return 'F', 0


# ─────────────────────────────────────────────────────────────
# 1. BATCH
# ─────────────────────────────────────────────────────────────

class Batch(models.Model):
    """
    Represents a year group: FY, SY, or TY.
    Students belong to one batch.
    Each batch covers 2 semesters.
    """
    name        = models.CharField(max_length=2, choices=BATCH_CHOICES, unique=True)
    academic_year = models.CharField(
        max_length=9,
        default='2025-26',
        help_text='e.g. 2025-26'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering  = ['name']
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'

    def __str__(self):
        return f'{self.get_name_display()} ({self.academic_year})'

    @property
    def semesters(self):
        """Returns the two semester numbers this batch covers."""
        return {
            'FY': [1, 2],
            'SY': [3, 4],
            'TY': [5, 6],
        }.get(self.name, [])

    @property
    def student_count(self):
        return self.students.count()


# ─────────────────────────────────────────────────────────────
# 2. STUDENT
# ─────────────────────────────────────────────────────────────

class Student(models.Model):
    """
    One Student record per physical student.
    Linked to Django's User model (for login).
    Roll number is the login username.
    Admin creates accounts — no self-registration.
    """
    user        = models.OneToOneField(
                    User,
                    on_delete=models.CASCADE,
                    related_name='student_profile'
                  )
    roll_number = models.CharField(
                    max_length=7,
                    unique=True,
                    validators=[validate_roll_number],
                    help_text='7-digit: 4-digit year + 3-digit serial (e.g. 2026001)'
                  )
    batch       = models.ForeignKey(
                    Batch,
                    on_delete=models.PROTECT,
                    related_name='students'
                  )
    full_name   = models.CharField(max_length=150)
    email       = models.EmailField(blank=True)
    phone       = models.CharField(max_length=15, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return f'{self.full_name} ({self.roll_number})'

    @property
    def initials(self):
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f'{parts[0][0]}{parts[-1][0]}'.upper()
        return self.full_name[:2].upper()

    @property
    def current_cgpa(self):
        try:
            return self.overall_result.cgpa
        except OverallResult.DoesNotExist:
            return None

    def get_semester_result(self, semester):
        return self.semester_results.filter(semester=semester).first()

    def save(self, *args, **kwargs):
        # Keep User.username in sync with roll_number
        if self.user and self.roll_number:
            self.user.username = self.roll_number
            self.user.save()
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────
# 3. SUBJECT
# ─────────────────────────────────────────────────────────────

class Subject(models.Model):
    """
    A subject in a given semester.
    Pre-loaded via fixtures (subjects.json) for all 6 sems.
    Admin can edit/add from Django admin panel.

    is_elective=True means admin must pick ONE from the
    elective group for that semester via SemesterElective.
    """
    semester      = models.IntegerField(choices=SEMESTER_CHOICES)
    code          = models.CharField(max_length=20, blank=True, help_text='Subject code from university')
    name          = models.CharField(max_length=200)
    subject_type  = models.CharField(max_length=2, choices=SUBJECT_TYPE_CHOICES, default='TH')
    group         = models.CharField(max_length=20, choices=SUBJECT_GROUP_CHOICES, default='Major')
    credits       = models.PositiveSmallIntegerField(default=2)
    ce_max        = models.PositiveSmallIntegerField(
                      default=20,
                      validators=[MaxValueValidator(20)],
                      verbose_name='CE Max Marks'
                    )
    ese_max       = models.PositiveSmallIntegerField(
                      default=30,
                      validators=[MaxValueValidator(30)],
                      verbose_name='ESE Max Marks'
                    )
    is_elective   = models.BooleanField(
                      default=False,
                      help_text='If True, admin selects one option per batch per semester'
                    )
    elective_group = models.CharField(
                      max_length=10, blank=True,
                      help_text='Group tag e.g. MJEL, MJELP — electives with same tag are mutually exclusive'
                    )
    is_active     = models.BooleanField(default=True)
    order         = models.PositiveSmallIntegerField(default=0, help_text='Display order in sem')

    class Meta:
        ordering = ['semester', 'order', 'name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __str__(self):
        return f'Sem {self.semester} | {self.name} ({self.get_subject_type_display()})'

    @property
    def total_max(self):
        return self.ce_max + self.ese_max

    @property
    def pass_marks(self):
        return round(self.total_max * settings.PASS_PERCENTAGE / 100)

    @property
    def type_badge(self):
        return 'type-theory' if self.subject_type == 'TH' else 'type-practical'


# ─────────────────────────────────────────────────────────────
# 4. SEMESTER ELECTIVE
# ─────────────────────────────────────────────────────────────

class SemesterElective(models.Model):
    """
    Admin picks ONE elective subject per batch per semester
    per elective group. That subject then applies to ALL
    students in that batch for that semester.

    e.g. For TY Sem V, admin picks MJEL1 (Software Testing)
         instead of MJEL2 (Wireless Networks).
         All TY students get MJEL1.
    """
    batch          = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='electives')
    semester       = models.IntegerField(choices=SEMESTER_CHOICES)
    elective_group = models.CharField(max_length=10, help_text='e.g. MJEL, MJELP')
    selected_subject = models.ForeignKey(
                         Subject,
                         on_delete=models.CASCADE,
                         related_name='selected_as_elective'
                       )
    set_by         = models.ForeignKey(
                       User, on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name='electives_set'
                     )
    set_at         = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('batch', 'semester', 'elective_group')
        verbose_name = 'Semester Elective'
        verbose_name_plural = 'Semester Electives'

    def __str__(self):
        return (f'{self.batch.name} Sem {self.semester} | '
                f'{self.elective_group}: {self.selected_subject.name}')


# ─────────────────────────────────────────────────────────────
# 5. MARKS
# ─────────────────────────────────────────────────────────────

class Marks(models.Model):
    """
    CE + ESE marks for one student for one subject.
    Grade and grade points are auto-calculated on save.
    One record per student-subject combination.
    """
    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks')
    subject    = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='marks')
    semester   = models.IntegerField(choices=SEMESTER_CHOICES)

    ce_marks   = models.DecimalField(
                   max_digits=4, decimal_places=1,
                   validators=[MinValueValidator(0)],
                   verbose_name='CE Marks (Internal)',
                   help_text='Max: subject ce_max (usually 20)'
                 )
    ese_marks  = models.DecimalField(
                   max_digits=4, decimal_places=1,
                   validators=[MinValueValidator(0)],
                   verbose_name='ESE Marks (Exam)',
                   help_text='Max: subject ese_max (usually 30)'
                 )

    # Auto-calculated on save — do not set manually
    total_marks   = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    percentage    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade         = models.CharField(max_length=2, choices=GRADE_CHOICES, default='F')
    grade_points  = models.PositiveSmallIntegerField(default=0)
    is_pass       = models.BooleanField(default=False)

    entered_by    = models.ForeignKey(
                      User, on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='marks_entered'
                    )
    entered_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'semester')
        verbose_name = 'Marks'
        verbose_name_plural = 'Marks'
        ordering = ['semester', 'student__roll_number']

    def __str__(self):
        return (f'{self.student.roll_number} | '
                f'Sem {self.semester} | {self.subject.name} | '
                f'{self.grade}')

    def clean(self):
        """Validate CE and ESE don't exceed subject max."""
        if self.ce_marks is not None and self.ce_marks > self.subject.ce_max:
            raise ValidationError(
                f'CE marks ({self.ce_marks}) cannot exceed '
                f'subject maximum ({self.subject.ce_max}).'
            )
        if self.ese_marks is not None and self.ese_marks > self.subject.ese_max:
            raise ValidationError(
                f'ESE marks ({self.ese_marks}) cannot exceed '
                f'subject maximum ({self.subject.ese_max}).'
            )

    def save(self, *args, **kwargs):
        """Auto-calculate total, percentage, grade, grade_points on every save."""
        self.total_marks  = self.ce_marks + self.ese_marks
        self.percentage   = round((self.total_marks / self.subject.total_max) * 100, 2)
        self.grade, self.grade_points = compute_grade(float(self.percentage))
        self.is_pass      = float(self.percentage) >= settings.PASS_PERCENTAGE
        super().save(*args, **kwargs)

    @property
    def grade_badge_class(self):
        mapping = {
            'O':  'badge-O',
            'A+': 'badge-Ap',
            'A':  'badge-A',
            'B+': 'badge-Bp',
            'B':  'badge-B',
            'C':  'badge-C',
            'F':  'badge-F',
        }
        return mapping.get(self.grade, 'badge-F')


# ─────────────────────────────────────────────────────────────
# 6. SEMESTER RESULT
# ─────────────────────────────────────────────────────────────

class SemesterResult(models.Model):
    """
    SGPA for one student for one semester.
    Calculated automatically when marks are published.

    SGPA formula:
      Σ(grade_points × credits) ÷ Σ(credits)
    """
    student    = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='semester_results')
    semester   = models.IntegerField(choices=SEMESTER_CHOICES)
    sgpa       = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    total_credits_earned = models.PositiveSmallIntegerField(default=0)
    total_credits        = models.PositiveSmallIntegerField(default=0)
    is_pass    = models.BooleanField(default=False)
    is_published = models.BooleanField(
                     default=False,
                     help_text='Set True when admin publishes — student can see results'
                   )
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
                     User, on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name='results_published'
                   )
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'semester')
        ordering = ['student__roll_number', 'semester']
        verbose_name = 'Semester Result'
        verbose_name_plural = 'Semester Results'

    def __str__(self):
        return (f'{self.student.roll_number} | '
                f'Sem {self.semester} | SGPA: {self.sgpa}')

    @property
    def result_label(self):
        return 'PASS' if self.is_pass else 'FAIL'

    @property
    def standing(self):
        """Returns human-readable standing from SGPA."""
        sgpa = float(self.sgpa)
        if sgpa >= 9.0: return 'Outstanding'
        if sgpa >= 8.0: return 'Excellent'
        if sgpa >= 7.0: return 'Very Good'
        if sgpa >= 6.0: return 'Good'
        if sgpa >= 5.0: return 'Average'
        return 'Below Average'

    def recalculate(self):
        """
        Recalculates SGPA from existing Marks records.
        Called by utils.calculate_sgpa() — do not call directly.
        """
        marks_qs = Marks.objects.filter(
            student=self.student,
            semester=self.semester
        ).select_related('subject')

        if not marks_qs.exists():
            return

        total_weighted = sum(
            float(m.grade_points) * m.subject.credits
            for m in marks_qs
        )
        total_credits = sum(m.subject.credits for m in marks_qs)
        earned_credits = sum(
            m.subject.credits for m in marks_qs if m.is_pass
        )

        self.sgpa = round(total_weighted / total_credits, 2) if total_credits else 0
        self.total_credits        = total_credits
        self.total_credits_earned = earned_credits
        self.is_pass = all(m.is_pass for m in marks_qs)
        self.save()


# ─────────────────────────────────────────────────────────────
# 7. OVERALL RESULT (CGPA)
# ─────────────────────────────────────────────────────────────

class OverallResult(models.Model):
    """
    CGPA for a student across all completed semesters.
    Recalculated every time a new semester result is published.

    CGPA formula:
      Average of all semester SGPAs
    """
    student            = models.OneToOneField(
                           Student, on_delete=models.CASCADE,
                           related_name='overall_result'
                         )
    cgpa               = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    semesters_completed = models.PositiveSmallIntegerField(default=0)
    last_updated       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Overall Result (CGPA)'
        verbose_name_plural = 'Overall Results (CGPA)'

    def __str__(self):
        return f'{self.student.roll_number} | CGPA: {self.cgpa}'

    @property
    def standing(self):
        cgpa = float(self.cgpa)
        if cgpa >= 9.0: return 'Outstanding'
        if cgpa >= 8.0: return 'Excellent'
        if cgpa >= 7.0: return 'Very Good'
        if cgpa >= 6.0: return 'Good'
        if cgpa >= 5.0: return 'Average'
        return 'Below Average'

    def recalculate(self):
        """
        Recalculates CGPA from all published SemesterResults.
        Called by utils.calculate_cgpa() — do not call directly.
        """
        published_results = SemesterResult.objects.filter(
            student=self.student,
            is_published=True
        )
        if not published_results.exists():
            return

        sgpa_list = [float(r.sgpa) for r in published_results]
        self.cgpa = round(sum(sgpa_list) / len(sgpa_list), 2)
        self.semesters_completed = published_results.count()
        self.save()
