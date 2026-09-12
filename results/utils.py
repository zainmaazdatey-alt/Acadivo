"""
Acadivo — Utility Functions
Step 6+: Grade calculation, SGPA/CGPA engine, CSV parsing.
PDF and email added in Steps 10-11.
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from django.conf import settings


# ── GRADE ENGINE ──────────────────────────────────────────────

GRADE_SCALE = getattr(settings, 'GRADE_SCALE', [
    (90, 'O',  10, 'Outstanding'),
    (75, 'A+',  9, 'Excellent'),
    (65, 'A',   8, 'Very Good'),
    (55, 'B+',  7, 'Good'),
    (50, 'B',   6, 'Above Average'),
    (40, 'C',   5, 'Average / Pass'),
    (0,  'F',   0, 'Fail'),
])


def compute_grade(percentage):
    """
    Returns (grade_letter, grade_points) from percentage (float/Decimal).
    NEP Mumbai University 10-point scale.
    """
    pct = float(percentage)
    for min_pct, grade, gp, _ in GRADE_SCALE:
        if pct >= min_pct:
            return grade, gp
    return 'F', 0


def grade_badge_class(grade):
    return {
        'O':  'badge-O',
        'A+': 'badge-Ap',
        'A':  'badge-A',
        'B+': 'badge-Bp',
        'B':  'badge-B',
        'C':  'badge-C',
        'F':  'badge-F',
    }.get(grade, 'badge-F')


# ── SGPA / CGPA ENGINE ───────────────────────────────────────

def calculate_sgpa(student, semester):
    """
    Calculate and save SGPA for a student for one semester.
    Creates or updates SemesterResult.
    Returns the SemesterResult instance.
    """
    from .models import Marks, SemesterResult

    marks_qs = Marks.objects.filter(
        student=student,
        semester=semester
    ).select_related('subject')

    if not marks_qs.exists():
        return None

    total_weighted = sum(
        float(m.grade_points) * m.subject.credits
        for m in marks_qs
    )
    total_credits  = sum(m.subject.credits for m in marks_qs)
    earned_credits = sum(m.subject.credits for m in marks_qs if m.is_pass)
    is_pass        = all(m.is_pass for m in marks_qs)
    sgpa = round(total_weighted / total_credits, 2) if total_credits else 0

    result, _ = SemesterResult.objects.update_or_create(
        student=student,
        semester=semester,
        defaults={
            'sgpa':                  Decimal(str(sgpa)),
            'total_credits':         total_credits,
            'total_credits_earned':  earned_credits,
            'is_pass':               is_pass,
        }
    )
    return result


def calculate_cgpa(student):
    """
    Calculate and save CGPA from all published SemesterResults.
    Creates or updates OverallResult.
    Returns the OverallResult instance.
    """
    from .models import SemesterResult, OverallResult

    published = SemesterResult.objects.filter(
        student=student,
        is_published=True
    )
    if not published.exists():
        return None

    sgpa_list = [float(r.sgpa) for r in published]
    cgpa      = round(sum(sgpa_list) / len(sgpa_list), 2)

    result, _ = OverallResult.objects.update_or_create(
        student=student,
        defaults={
            'cgpa':                Decimal(str(cgpa)),
            'semesters_completed': published.count(),
        }
    )
    return result


# ── CSV PARSING ───────────────────────────────────────────────

# Expected CSV columns (case-insensitive, strip spaces):
# roll_number, subject_code OR subject_id, semester, ce_marks, ese_marks
REQUIRED_CSV_COLS = {'roll_number', 'semester', 'ce_marks', 'ese_marks'}


def parse_marks_csv(file_obj, entered_by=None):
    """
    Parse a CSV file and save/update Marks records.

    Returns:
        {
          'saved':   int,   # rows successfully saved
          'skipped': int,   # rows skipped (already exist, not overwriting)
          'errors':  list,  # list of (row_num, error_message) tuples
        }

    CSV format (header row required):
        roll_number, subject_id, semester, ce_marks, ese_marks

    OR with subject code:
        roll_number, subject_code, semester, ce_marks, ese_marks
    """
    from .models import Student, Subject, Marks

    results = {'saved': 0, 'skipped': 0, 'errors': []}

    try:
        decoded = file_obj.read().decode('utf-8-sig')  # handle BOM
        reader  = csv.DictReader(io.StringIO(decoded))
    except Exception as e:
        results['errors'].append((0, f'Cannot read CSV file: {e}'))
        return results

    # Normalise header names
    if reader.fieldnames is None:
        results['errors'].append((0, 'CSV file is empty or has no header row.'))
        return results

    headers = {h.strip().lower().replace(' ', '_') for h in reader.fieldnames}
    missing = REQUIRED_CSV_COLS - headers
    if missing:
        results['errors'].append(
            (0, f'Missing columns: {", ".join(missing)}. '
                f'Required: roll_number, semester, ce_marks, ese_marks, '
                f'and either subject_id or subject_code.')
        )
        return results

    has_subject_id   = 'subject_id'   in headers
    has_subject_code = 'subject_code' in headers
    if not has_subject_id and not has_subject_code:
        results['errors'].append(
            (0, 'CSV must have either "subject_id" or "subject_code" column.')
        )
        return results

    for row_num, raw_row in enumerate(reader, start=2):
        # Normalise keys
        row = {k.strip().lower().replace(' ', '_'): v.strip()
               for k, v in raw_row.items() if k}

        roll     = row.get('roll_number', '').strip()
        semester = row.get('semester', '').strip()
        ce_raw   = row.get('ce_marks', '').strip()
        ese_raw  = row.get('ese_marks', '').strip()

        # ── Validate roll number ──
        try:
            student = Student.objects.get(roll_number=roll, is_active=True)
        except Student.DoesNotExist:
            results['errors'].append((row_num, f'Roll number "{roll}" not found.'))
            continue

        # ── Validate semester ──
        try:
            semester_int = int(semester)
            if semester_int not in range(1, 7):
                raise ValueError
        except ValueError:
            results['errors'].append((row_num, f'Invalid semester "{semester}". Must be 1–6.'))
            continue

        # ── Resolve subject ──
        subject = None
        if has_subject_id:
            subj_id = row.get('subject_id', '').strip()
            try:
                subject = Subject.objects.get(pk=int(subj_id), is_active=True)
            except (Subject.DoesNotExist, ValueError):
                results['errors'].append((row_num, f'Subject ID "{subj_id}" not found.'))
                continue
        elif has_subject_code:
            subj_code = row.get('subject_code', '').strip()
            try:
                subject = Subject.objects.get(code=subj_code, is_active=True)
            except Subject.DoesNotExist:
                results['errors'].append((row_num, f'Subject code "{subj_code}" not found.'))
                continue
            except Subject.MultipleObjectsReturned:
                results['errors'].append((row_num, f'Multiple subjects with code "{subj_code}".'))
                continue

        # ── Validate marks ──
        try:
            ce_marks  = Decimal(ce_raw)
            ese_marks = Decimal(ese_raw)
        except InvalidOperation:
            results['errors'].append((row_num, f'Invalid marks: CE="{ce_raw}", ESE="{ese_raw}".'))
            continue

        if ce_marks < 0 or ce_marks > subject.ce_max:
            results['errors'].append(
                (row_num, f'CE marks {ce_marks} out of range (0–{subject.ce_max}).')
            )
            continue
        if ese_marks < 0 or ese_marks > subject.ese_max:
            results['errors'].append(
                (row_num, f'ESE marks {ese_marks} out of range (0–{subject.ese_max}).')
            )
            continue

        # ── Save or update Marks ──
        try:
            marks, created = Marks.objects.update_or_create(
                student=student,
                subject=subject,
                semester=semester_int,
                defaults={
                    'ce_marks':   ce_marks,
                    'ese_marks':  ese_marks,
                    'entered_by': entered_by,
                }
            )
            # Trigger auto-calculation (Marks.save() computes grade/total/pct)
            marks.save()
            results['saved'] += 1
        except Exception as e:
            results['errors'].append((row_num, f'Database error: {e}'))
            continue

    return results


def generate_excel_template(semester, batch):
    """
    Generate a styled Excel (.xlsx) marks entry template matching the
    Acadivo Obsidian Violet design — same layout as the demo template.

    Layout:
      Row 1  : Title banner (dark bg, white bold text)
      Row 2  : Batch | TY  | Semester | Sem V | Academic Year | 2025-26
      Row 4  : Subject names (merged across CE/ESE/Total cols, violet bg)
      Row 5  : Column headers: Roll Number | Student Name | CE | ESE | Total/Grade ...
      Row 6+ : One row per student, CE and ESE blank (to fill), Total grayed out
      Last   : Instruction note

    Returns: BytesIO buffer (xlsx)
    """
    import io
    from openpyxl import Workbook
    from openpyxl.styles import (
        PatternFill, Font, Alignment, Border, Side, Protection
    )
    from openpyxl.utils import get_column_letter
    from .models import Subject, Student, SemesterElective
    from django.conf import settings

    # ── Colours (match Obsidian Violet) ──
    C_DARK    = '100D1A'   # title bg
    C_ACCENT  = '9D6FFF'   # subject header bg
    C_ACCENT2 = 'BFA3FF'   # light violet
    C_META_BG = 'EDE7FA'   # batch/sem info bg
    C_HDR_BG  = 'D6CCFF'   # column header bg
    C_WHITE   = 'FFFFFF'
    C_TEXT    = '222222'
    C_MUTED   = '7A70A0'
    C_INPUT   = 'F4F1FF'   # CE/ESE input cells (light violet tint)
    C_LOCKED  = 'F0F0F0'   # Total/Grade read-only cells
    C_ALT     = 'FAF8FF'   # alternate student rows
    C_GREEN   = '34D399'
    C_BORDER  = 'C8C0E8'

    acad_year = getattr(settings, 'ACADEMIC_YEAR', '2025-26')
    college   = getattr(settings, 'COLLEGE_NAME', 'Anjuman Islam Janjira Degree College')

    # ── Helpers ──
    def fill(hex_col):
        return PatternFill('solid', fgColor=hex_col)

    def font(bold=False, color=C_TEXT, size=10, name='Calibri'):
        return Font(bold=bold, color=color, size=size, name=name)

    def align(h='center', v='center', wrap=False):
        return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

    def thin_border(sides='all'):
        s = Side(style='thin', color=C_BORDER)
        n = Side(style=None)
        if sides == 'all':
            return Border(left=s, right=s, top=s, bottom=s)
        return Border(
            left =s if 'l' in sides else n,
            right=s if 'r' in sides else n,
            top  =s if 't' in sides else n,
            bottom=s if 'b' in sides else n,
        )

    # ── Get subjects ──
    non_elective = list(Subject.objects.filter(
        semester=semester, is_active=True, is_elective=False
    ).order_by('order'))
    elected = SemesterElective.objects.filter(
        batch=batch, semester=semester
    ).select_related('selected_subject')
    elective_subjects = [e.selected_subject for e in elected]
    subjects = non_elective + elective_subjects

    students = list(Student.objects.filter(
        batch=batch, is_active=True
    ).order_by('roll_number'))

    # ── Workbook setup ──
    wb = Workbook()
    ws = wb.active
    ws.title = f'Semester {semester} Marks'
    ws.sheet_view.showGridLines = False

    # Each subject gets 3 columns: CE | ESE | Total/Grade
    FIXED_COLS  = 2          # Roll + Name
    COLS_PER_SUBJ = 3        # CE, ESE, Total
    total_cols  = FIXED_COLS + len(subjects) * COLS_PER_SUBJ

    # ── Column widths ──
    ws.column_dimensions['A'].width = 14   # Roll number
    ws.column_dimensions['B'].width = 22   # Student name
    for i, subj in enumerate(subjects):
        base = FIXED_COLS + i * COLS_PER_SUBJ  # 0-indexed
        ws.column_dimensions[get_column_letter(base + 1)].width = 8   # CE
        ws.column_dimensions[get_column_letter(base + 2)].width = 8   # ESE
        ws.column_dimensions[get_column_letter(base + 3)].width = 11  # Total

    # ── ROW 1: Title banner ──
    ws.row_dimensions[1].height = 28
    title_cell = ws.cell(1, 1,
        value=f'ACADIVO — SEMESTER {semester} MARKS ENTRY TEMPLATE')
    title_cell.fill      = fill(C_DARK)
    title_cell.font      = font(bold=True, color=C_WHITE, size=13)
    title_cell.alignment = align('left')
    ws.merge_cells(start_row=1, start_column=1,
                   end_row=1, end_column=total_cols)

    # ── ROW 2: Meta info ──
    ws.row_dimensions[2].height = 18
    meta = [
        (1, 'BATCH',         C_META_BG, C_ACCENT, True),
        (2, batch.get_name_display(), C_WHITE, C_TEXT, True),
        (3, None, C_WHITE, C_TEXT, False),
        (4, 'SEMESTER',      C_META_BG, C_ACCENT, True),
        (5, f'Semester {semester}', C_WHITE, C_TEXT, True),
        (6, None, C_WHITE, C_TEXT, False),
        (7, 'ACADEMIC YEAR', C_META_BG, C_ACCENT, True),
        (8, acad_year,       C_WHITE, C_TEXT, True),
    ]
    for col, val, bg, fg, bold in meta:
        c = ws.cell(2, col, value=val)
        c.fill      = fill(bg)
        c.font      = font(bold=bold, color=fg, size=9)
        c.alignment = align('left')

    # ── ROW 3: blank spacer ──
    ws.row_dimensions[3].height = 6

    # ── ROW 4: Subject name headers (merged across 3 cols each) ──
    ws.row_dimensions[4].height = 36
    for i, subj in enumerate(subjects):
        start_col = FIXED_COLS + 1 + i * COLS_PER_SUBJ
        end_col   = start_col + COLS_PER_SUBJ - 1
        ws.merge_cells(start_row=4, start_column=start_col,
                       end_row=4, end_column=end_col)
        c = ws.cell(4, start_col, value=subj.name.upper())
        c.fill      = fill(C_ACCENT)
        c.font      = font(bold=True, color=C_WHITE, size=9)
        c.alignment = align('center', wrap=True)

    # Empty cells under fixed cols row 4
    for col in range(1, FIXED_COLS + 1):
        c = ws.cell(4, col)
        c.fill = fill(C_DARK)

    # ── ROW 5: Column headers ──
    ws.row_dimensions[5].height = 20
    # Fixed headers
    for col, label in [(1, 'ROLL NUMBER'), (2, 'STUDENT NAME')]:
        c = ws.cell(5, col, value=label)
        c.fill      = fill(C_HDR_BG)
        c.font      = font(bold=True, color='4B0082', size=9)
        c.alignment = align('center')
        c.border    = thin_border()

    # Subject col headers
    for i, subj in enumerate(subjects):
        base = FIXED_COLS + i * COLS_PER_SUBJ
        ce_label = f'CE /{subj.ce_max}'
        ese_label= f'ESE /{subj.ese_max}'
        for offset, label in enumerate([ce_label, ese_label, 'TOTAL/GRADE']):
            c = ws.cell(5, base + offset + 1, value=label)
            c.fill      = fill(C_HDR_BG)
            c.font      = font(bold=True, color='4B0082', size=8)
            c.alignment = align('center')
            c.border    = thin_border()

    # ── ROW 6+ : Student data rows ──
    for row_idx, student in enumerate(students):
        row = 6 + row_idx
        ws.row_dimensions[row].height = 18
        is_alt = row_idx % 2 == 1

        # Roll number
        rc = ws.cell(row, 1, value=student.roll_number)
        rc.font      = font(bold=True, size=10)
        rc.alignment = align('center')
        rc.fill      = fill(C_ALT if is_alt else C_WHITE)
        rc.border    = thin_border()

        # Student name
        nc = ws.cell(row, 2, value=student.full_name)
        nc.font      = font(bold=True, size=10)
        nc.alignment = align('left')
        nc.fill      = fill(C_ALT if is_alt else C_WHITE)
        nc.border    = thin_border()

        # Subject marks columns
        for i, subj in enumerate(subjects):
            base = FIXED_COLS + i * COLS_PER_SUBJ

            # CE input cell
            ce_cell = ws.cell(row, base + 1, value=None)
            ce_cell.fill      = fill(C_INPUT)
            ce_cell.alignment = align('center')
            ce_cell.border    = thin_border()
            ce_cell.font      = font(size=10)

            # ESE input cell
            ese_cell = ws.cell(row, base + 2, value=None)
            ese_cell.fill      = fill(C_INPUT)
            ese_cell.alignment = align('center')
            ese_cell.border    = thin_border()
            ese_cell.font      = font(size=10)

            # Total/Grade (read-only hint)
            tot_cell = ws.cell(row, base + 3, value='auto')
            tot_cell.fill      = fill(C_LOCKED)
            tot_cell.alignment = align('center')
            tot_cell.border    = thin_border()
            tot_cell.font      = font(color=C_MUTED, size=9)

    # ── Last row: instruction note ──
    note_row = 6 + len(students)
    ws.row_dimensions[note_row].height = 16
    note = ws.cell(note_row, 1,
        value='⚠  ENTER CE AND ESE MARKS ONLY. '
              'TOTAL / GRADE IS AUTO-CALCULATED BY ACADIVO AFTER UPLOAD. '
              'DO NOT MODIFY ROLL NUMBER OR STUDENT NAME COLUMNS.')
    note.fill      = fill('FFF8E1')
    note.font      = font(bold=False, color='7A5C00', size=8)
    note.alignment = align('left')
    ws.merge_cells(start_row=note_row, start_column=1,
                   end_row=note_row, end_column=total_cols)

    # ── Freeze panes at C6 (keep roll+name visible when scrolling) ──
    ws.freeze_panes = 'C6'

    # ── Save to buffer ──
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# Keep old name as alias for CSV (used by parse_marks_csv)
def generate_csv_template(semester, batch):
    """Legacy CSV template — use generate_excel_template for the styled xlsx version."""
    import io
    from .models import Subject, Student, SemesterElective

    subjects = list(Subject.objects.filter(
        semester=semester, is_active=True, is_elective=False
    ).order_by('order'))
    elected = SemesterElective.objects.filter(
        batch=batch, semester=semester
    ).select_related('selected_subject')
    subjects += [e.selected_subject for e in elected]

    output  = io.StringIO()
    writer  = csv.writer(output)
    writer.writerow(['roll_number', 'subject_id', 'subject_code',
                     'semester', 'ce_marks', 'ese_marks', 'subject_name'])
    for student in Student.objects.filter(batch=batch, is_active=True).order_by('roll_number'):
        for subj in subjects:
            writer.writerow([student.roll_number, subj.pk, subj.code or '',
                             semester, '', '', subj.name])
    return output.getvalue()


# ── EMAIL NOTIFICATION ────────────────────────────────────────

def send_result_email(student, sem_result):
    """
    Send result notification email to a student.
    Returns (True, None) on success, (False, error_str) on failure.

    Uses Django's email backend:
      - Development: console backend (prints to terminal)
      - Production:  set EMAIL_BACKEND=smtp in .env
    """
    from django.core.mail import send_mail
    from django.conf import settings

    if not student.email:
        return False, 'No email address on record'

    college   = getattr(settings, 'COLLEGE_NAME', 'Anjuman Islam Janjira Degree College of Science')
    program   = getattr(settings, 'COLLEGE_PROGRAM', 'BSc Computer Science (NEP)')
    acad_year = getattr(settings, 'ACADEMIC_YEAR', '2025-26')

    standing  = sem_result.standing
    pass_fail = 'PASS' if sem_result.is_pass else 'FAIL'

    subject = (
        f'[Acadivo] Semester {sem_result.semester} Result Published — '
        f'{pass_fail} | {college}'
    )

    body = f"""Dear {student.full_name},

Your Semester {sem_result.semester} result has been published on the Acadivo Student Portal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESULT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Student Name  : {student.full_name}
Roll Number   : {student.roll_number}
Batch         : {student.batch.get_name_display()}
Semester      : {sem_result.semester}
SGPA          : {sem_result.sgpa}
Credits Earned: {sem_result.total_credits_earned} / {sem_result.total_credits}
Standing      : {standing}
Result        : {pass_fail}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Log in to the Acadivo portal to view your full subject-wise marks
and download your PDF marksheet.

Portal URL: http://127.0.0.1:8000/login/

Regards,
Examination Department
{college}
{program} | Academic Year {acad_year}

──────────────────────────────
This is an automated message from the Acadivo Result Portal.
Please do not reply to this email.
"""

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        return True, None
    except Exception as e:
        return False, str(e)


# ── PDF MARKSHEET GENERATION ─────────────────────────────────

def generate_marksheet_pdf(student, semester):
    """
    Generate a professional A4 PDF marksheet.
    Includes: college logo, header bar, student info, subject marks table,
    result summary strip, PASS/FAIL stamp, and footer.
    """
    import io
    import os
    from datetime import date
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas as rl_canvas
    from django.conf import settings

    # ── Colours ──
    C_DARK   = colors.HexColor('#100D1A')
    C_CARD   = colors.HexColor('#1A1628')
    C_ACCENT = colors.HexColor('#9D6FFF')
    C_ACCT2  = colors.HexColor('#BFA3FF')
    C_TEXT   = colors.HexColor('#1A1628')   # dark for print
    C_MUTED  = colors.HexColor('#5A5080')
    C_GREEN  = colors.HexColor('#1A7A50')   # dark green for print
    C_RED    = colors.HexColor('#B03030')
    C_AMBER  = colors.HexColor('#8A6000')
    C_WHITE  = colors.white
    C_BORDER = colors.HexColor('#D0C8E8')
    C_HDRBG  = colors.HexColor('#EDE7FA')   # light violet tint for table header
    C_ALT    = colors.HexColor('#F8F5FF')   # alternate row
    C_STAMP_PASS = colors.HexColor('#1A7A50')
    C_STAMP_FAIL = colors.HexColor('#B03030')

    # ── Data fetch ──
    from .models import Marks, SemesterResult, OverallResult

    marks_qs   = Marks.objects.filter(
        student=student, semester=semester
    ).select_related('subject').order_by('subject__order')

    sem_result = SemesterResult.objects.filter(
        student=student, semester=semester, is_published=True
    ).first()

    overall = OverallResult.objects.filter(student=student).first()

    college   = getattr(settings, 'COLLEGE_NAME',    'Anjuman Islam Janjira Degree College of Science')
    location  = getattr(settings, 'COLLEGE_LOCATION','Murud-Janjira, Raigad, Maharashtra')
    affil     = getattr(settings, 'COLLEGE_AFF',     'Affiliated to University of Mumbai')
    program   = getattr(settings, 'COLLEGE_PROGRAM', 'BSc Computer Science (NEP)')
    acad_year = getattr(settings, 'ACADEMIC_YEAR',   '2025-26')

    LOGO_PATH = os.path.join(
        settings.BASE_DIR, 'results', 'static', 'results', 'img', 'logo.png'
    )
    PAGE_W, PAGE_H = A4
    MARGIN = 1.6 * cm
    HEADER_H = 3.6 * cm

    buffer = io.BytesIO()

    # ── Custom canvas for fixed header/footer/stamp ──
    class MarksheetCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_pages = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for i, page in enumerate(self._saved_pages):
                self.__dict__.update(page)
                self._draw_header()
                self._draw_footer(i + 1, total)
                if sem_result:
                    self._draw_stamp()
                super().showPage()
            super().save()

        def _draw_header(self):
            # ── Dark background ──
            self.setFillColor(C_DARK)
            self.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

            # ── Violet top accent line ──
            self.setFillColor(C_ACCENT)
            self.rect(0, PAGE_H - 3, PAGE_W, 3, fill=1, stroke=0)

            # ── Left violet side bar ──
            self.setFillColor(C_ACCENT)
            self.rect(0, PAGE_H - HEADER_H, 5, HEADER_H - 3, fill=1, stroke=0)

            # ── Logo ──
            LOGO_SIZE = 1.8 * cm
            LOGO_X    = MARGIN
            LOGO_Y    = PAGE_H - HEADER_H + (HEADER_H - LOGO_SIZE) / 2
            if os.path.exists(LOGO_PATH):
                try:
                    self.drawImage(
                        LOGO_PATH, LOGO_X, LOGO_Y,
                        width=LOGO_SIZE, height=LOGO_SIZE,
                        preserveAspectRatio=True, mask='auto'
                    )
                except Exception:
                    self._draw_logo_fallback(LOGO_X, LOGO_Y, LOGO_SIZE)
            else:
                self._draw_logo_fallback(LOGO_X, LOGO_Y, LOGO_SIZE)

            TEXT_X = MARGIN + LOGO_SIZE + 0.4 * cm

            # ── College name ──
            self.setFillColor(C_WHITE)
            self.setFont('Helvetica-Bold', 13)
            self.drawString(TEXT_X, PAGE_H - 1.1 * cm, college)

            # ── Location + affiliation ──
            self.setFillColor(C_ACCT2)
            self.setFont('Helvetica', 8.5)
            self.drawString(TEXT_X, PAGE_H - 1.7 * cm,
                            f'{location}  ·  {affil}')

            # ── Program + year ──
            self.setFillColor(colors.HexColor('#7A70A0'))
            self.setFont('Helvetica', 8)
            self.drawString(TEXT_X, PAGE_H - 2.2 * cm,
                            f'{program}  ·  Academic Year {acad_year}')

            # ── Right side: MARKSHEET label ──
            self.setFillColor(C_ACCENT)
            self.roundRect(PAGE_W - MARGIN - 3.2*cm,
                           PAGE_H - HEADER_H + 1.0*cm,
                           3.2*cm, 1.1*cm, 4, fill=1, stroke=0)
            self.setFillColor(C_WHITE)
            self.setFont('Helvetica-Bold', 11)
            self.drawCentredString(
                PAGE_W - MARGIN - 1.6*cm,
                PAGE_H - HEADER_H + 1.45*cm,
                'MARKSHEET'
            )
            self.setFillColor(colors.HexColor('#BFA3FF'))
            self.setFont('Helvetica', 7.5)
            self.drawCentredString(
                PAGE_W - MARGIN - 1.6*cm,
                PAGE_H - HEADER_H + 0.55*cm,
                f'Semester {semester}  ·  NEP 10-pt'
            )

            # ── Thin separator line at bottom of header ──
            self.setStrokeColor(C_ACCENT)
            self.setLineWidth(0.8)
            self.line(MARGIN, PAGE_H - HEADER_H - 0.15*cm,
                      PAGE_W - MARGIN, PAGE_H - HEADER_H - 0.15*cm)

        def _draw_logo_fallback(self, x, y, size):
            """Draw violet 'A' box if logo file not found."""
            self.setFillColor(C_ACCENT)
            self.roundRect(x, y, size, size, 5, fill=1, stroke=0)
            self.setFillColor(C_WHITE)
            self.setFont('Helvetica-Bold', 20)
            self.drawCentredString(x + size/2, y + size*0.3, 'A')

        def _draw_footer(self, page_num, total):
            FY = 0.6 * cm
            self.setStrokeColor(C_ACCENT)
            self.setLineWidth(0.5)
            self.line(MARGIN, FY + 0.6*cm, PAGE_W - MARGIN, FY + 0.6*cm)
            self.setFillColor(C_MUTED)
            self.setFont('Helvetica', 7)
            self.drawString(MARGIN, FY + 0.2*cm,
                f'Generated by Acadivo Result Portal  ·  {date.today().strftime("%d %B %Y")}  ·  '
                f'University of Mumbai Affiliated  ·  Confidential Document')
            self.drawRightString(PAGE_W - MARGIN, FY + 0.2*cm,
                f'Page {page_num} of {total}')

        def _draw_stamp(self):
            """Draw diagonal PASS / FAIL stamp on right side of page."""
            if not sem_result:
                return
            is_pass = sem_result.is_pass
            label   = 'PASS' if is_pass else 'FAIL'
            col     = C_STAMP_PASS if is_pass else C_STAMP_FAIL

            self.saveState()
            # Position: lower-right area
            cx = PAGE_W - MARGIN - 2.5*cm
            cy = MARGIN + 5.5*cm

            self.translate(cx, cy)
            self.rotate(345)   # slight tilt

            # Outer rect (border)
            self.setStrokeColor(col)
            self.setLineWidth(2.5)
            self.setFillColor(colors.Color(
                col.red, col.green, col.blue, alpha=0.06
            ))
            self.roundRect(-1.8*cm, -0.55*cm, 3.6*cm, 1.1*cm, 6,
                           fill=1, stroke=1)

            # Text
            self.setFillColor(col)
            self.setFont('Helvetica-Bold', 20)
            self.drawCentredString(0, -0.22*cm, label)

            self.restoreState()

    # ── Build document ──
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=HEADER_H + 0.5*cm,
        bottomMargin=1.8*cm,
        title=f'Marksheet – {student.full_name} – Semester {semester}',
        author='Acadivo Result Portal',
    )

    story = []

    # ── Student info table ──
    def ps(name, **kw):
        defaults = dict(fontName='Helvetica', fontSize=9,
                        textColor=C_TEXT, leading=12)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    info_rows = [
        [
            Paragraph('<b>Student Name</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(f'<b>{student.full_name}</b>',
                      ps('val', fontName='Helvetica-Bold', fontSize=11)),
            Paragraph('<b>Roll Number</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(f'<b>{student.roll_number}</b>',
                      ps('val', fontName='Courier-Bold', fontSize=11,
                         textColor=colors.HexColor('#4B0082'))),
        ],
        [
            Paragraph('<b>Batch</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(student.batch.get_name_display(), ps('val')),
            Paragraph('<b>Semester</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(f'Semester {semester}', ps('val')),
        ],
        [
            Paragraph('<b>Program</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(program, ps('val')),
            Paragraph('<b>Academic Year</b>', ps('lbl', textColor=C_MUTED, fontSize=8)),
            Paragraph(acad_year, ps('val')),
        ],
    ]
    info_t = Table(info_rows, colWidths=[2.8*cm, 8.2*cm, 2.8*cm, 4.5*cm])
    info_t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), colors.HexColor('#F8F5FF')),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.HexColor('#F4F0FF'),
                                         colors.HexColor('#FAF8FF'),
                                         colors.HexColor('#F4F0FF')]),
        ('BOX',          (0,0), (-1,-1), 1,   C_BORDER),
        ('INNERGRID',    (0,0), (-1,-1), 0.4, C_BORDER),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('LINEAFTER',    (1,0), (1,-1),  1,   C_BORDER),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 0.45*cm))

    # ── Section heading ──
    story.append(Paragraph(
        'SUBJECT-WISE MARKS',
        ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=7.5,
                       textColor=C_MUTED, spaceBefore=2, spaceAfter=5,
                       letterSpacing=1.5, leading=10)
    ))

    # ── Grade colour mapping ──
    GRADE_FG = {
        'O':  colors.HexColor('#1A7A50'),
        'A+': colors.HexColor('#4B0082'),
        'A':  colors.HexColor('#1A4A8A'),
        'B+': colors.HexColor('#5A1A8A'),
        'B':  colors.HexColor('#7A5C00'),
        'C':  colors.HexColor('#8A4500'),
        'F':  colors.HexColor('#B03030'),
    }

    def th(txt):
        return Paragraph(txt, ParagraphStyle('th',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=C_MUTED, alignment=TA_CENTER, leading=10))

    def tc(txt, bold=False, color=None, align=TA_LEFT, size=9, font='Helvetica'):
        return Paragraph(txt, ParagraphStyle('td',
            fontName=f'{font}{"-Bold" if bold else ""}',
            fontSize=size, textColor=color or C_TEXT,
            alignment=align, leading=11))

    marks_rows = [[
        th('SUBJECT'), th('TYPE'), th(f'CE'), th(f'ESE'),
        th('TOTAL'), th('%'), th('GRADE'), th('GP'), th('CR'),
    ]]

    row_styles = []
    for i, mark in enumerate(marks_qs, start=1):
        gcol = GRADE_FG.get(mark.grade, C_TEXT)
        pct  = float(mark.percentage)
        tcol = C_GREEN if pct >= 65 else (C_TEXT if pct >= 40 else C_RED)
        bg   = colors.HexColor('#FFF5F5') if not mark.is_pass else (
               C_ALT if i % 2 == 0 else C_WHITE)
        row_styles.append(('BACKGROUND', (0,i), (-1,i), bg))

        marks_rows.append([
            Paragraph(mark.subject.name,
                      ParagraphStyle('sn', fontName='Helvetica', fontSize=8.5,
                                     textColor=C_TEXT, leading=11)),
            tc('Theory' if mark.subject.subject_type == 'TH' else 'Practical',
               color=C_MUTED, align=TA_CENTER, size=7.5),
            tc(str(mark.ce_marks),  align=TA_CENTER, font='Courier'),
            tc(str(mark.ese_marks), align=TA_CENTER, font='Courier'),
            tc(str(mark.total_marks), bold=True, color=tcol,
               align=TA_CENTER, font='Courier'),
            tc(f'{mark.percentage}%', color=C_MUTED, align=TA_CENTER,
               size=8, font='Courier'),
            tc(mark.grade, bold=True, color=gcol,
               align=TA_CENTER, size=10, font='Courier'),
            tc(str(mark.grade_points), bold=True, color=gcol,
               align=TA_CENTER, font='Courier'),
            tc(str(mark.subject.credits), align=TA_CENTER, font='Courier'),
        ])

    COL_W = [6.2*cm, 1.7*cm, 1.1*cm, 1.1*cm, 1.3*cm,
             1.5*cm, 1.3*cm, 0.9*cm, 0.9*cm]
    marks_t = Table(marks_rows, colWidths=COL_W, repeatRows=1)
    ts_cmds = [
        ('BACKGROUND',   (0,0), (-1,0),  C_DARK),
        ('LINEBELOW',    (0,0), (-1,0),  1.2, C_ACCENT),
        ('BOX',          (0,0), (-1,-1), 0.6, C_BORDER),
        ('INNERGRID',    (0,1), (-1,-1), 0.3, C_BORDER),
        ('TOPPADDING',   (0,0), (-1,0),  8),
        ('BOTTOMPADDING',(0,0), (-1,0),  8),
        ('TOPPADDING',   (0,1), (-1,-1), 6),
        ('BOTTOMPADDING',(0,1), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
    ] + row_styles
    marks_t.setStyle(TableStyle(ts_cmds))
    story.append(marks_t)
    story.append(Spacer(1, 0.5*cm))

    # ── Result summary ──
    if sem_result:
        sgpa_val = float(sem_result.sgpa)
        sgpa_col = (C_GREEN if sgpa_val >= 9 else
                    colors.HexColor('#4B0082') if sgpa_val >= 7 else C_AMBER)
        res_col  = C_STAMP_PASS if sem_result.is_pass else C_STAMP_FAIL

        sum_data = [[
            Paragraph('SGPA', ps('sl', textColor=C_MUTED,
                                  fontSize=7, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER)),
            Paragraph('CREDITS EARNED', ps('sl', textColor=C_MUTED,
                                            fontSize=7, fontName='Helvetica-Bold',
                                            alignment=TA_CENTER)),
            Paragraph('STANDING', ps('sl', textColor=C_MUTED,
                                      fontSize=7, fontName='Helvetica-Bold',
                                      alignment=TA_CENTER)),
            Paragraph('RESULT', ps('sl', textColor=C_MUTED,
                                    fontSize=7, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER)),
            Paragraph('CGPA', ps('sl', textColor=C_MUTED,
                                  fontSize=7, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER)),
        ],[
            Paragraph(str(sem_result.sgpa),
                      ps('sv', fontName='Helvetica-Bold', fontSize=22,
                         textColor=sgpa_col, alignment=TA_CENTER)),
            Paragraph(f'{sem_result.total_credits_earned} / {sem_result.total_credits}',
                      ps('sv', fontName='Courier-Bold', fontSize=13,
                         textColor=C_TEXT, alignment=TA_CENTER)),
            Paragraph(sem_result.standing,
                      ps('sv', fontName='Helvetica-Bold', fontSize=11,
                         textColor=colors.HexColor('#4B0082'), alignment=TA_CENTER)),
            Paragraph('PASS' if sem_result.is_pass else 'FAIL',
                      ps('sv', fontName='Helvetica-Bold', fontSize=17,
                         textColor=res_col, alignment=TA_CENTER)),
            Paragraph(str(overall.cgpa) if overall else '—',
                      ps('sv', fontName='Helvetica-Bold', fontSize=22,
                         textColor=colors.HexColor('#4B0082'), alignment=TA_CENTER)),
        ]]

        W = PAGE_W - 2 * MARGIN
        sum_t = Table(sum_data,
                      colWidths=[W*0.17, W*0.23, W*0.23, W*0.17, W*0.20])
        sum_t.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,-1), colors.HexColor('#F4F0FF')),
            ('BOX',          (0,0), (-1,-1), 0.8, C_BORDER),
            ('INNERGRID',    (0,0), (-1,-1), 0.4, C_BORDER),
            ('LINEABOVE',    (0,0), (-1,0),  2.5, C_ACCENT),
            ('TOPPADDING',   (0,0), (-1,0),  7),
            ('BOTTOMPADDING',(0,0), (-1,0),  5),
            ('TOPPADDING',   (0,1), (-1,1),  6),
            ('BOTTOMPADDING',(0,1), (-1,1), 10),
            ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND',   (3,0), (3,-1),
             colors.HexColor('#FFF0F0' if not sem_result.is_pass else '#F0FFF4')),
        ]))
        story.append(sum_t)

    doc.build(story, canvasmaker=MarksheetCanvas)
    buffer.seek(0)
    return buffer
