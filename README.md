# Acadivo — Student Result Portal

**BSc Computer Science (NEP) · Anjuman Islam Janjira Degree College of Science**
**University of Mumbai · Django + SQLite · Obsidian Violet UI**

---

## Quick Start — Run in 5 Minutes

### 1. Extract and enter the project folder
```bash
cd acadivo_step1
```

### 2. Create virtual environment and install packages
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Set up the database
```bash
python manage.py migrate
```

### 4. Load NEP subjects + create demo accounts
```bash
python manage.py loaddata results/fixtures/subjects.json
python manage.py setup_demo
```

This creates:

| Role    | Username | Password        |
|---------|----------|-----------------|
| Admin   | admin    | admin@acadivo   |
| FY Demo | 2026001  | student@acadivo |
| SY Demo | 2025001  | student@acadivo |
| TY Demo | 2024001  | student@acadivo |

### 5. Run the server
```bash
python manage.py runserver
```

- **Login page:** http://127.0.0.1:8000/login/
- **Admin panel:** http://127.0.0.1:8000/admin/

---

## Project Structure

```
acadivo_step1/
├── acadivo/
│   ├── settings.py          ← All config: SQLite, Gmail, grading constants
│   ├── urls.py              ← Root URL router
│   └── wsgi.py / asgi.py
│
├── results/
│   ├── models.py            ← 7 DB tables
│   ├── views.py             ← All page logic
│   ├── urls.py              ← All routes (18 named URLs)
│   ├── forms.py             ← StudentForm, SubjectForm
│   ├── admin.py             ← Obsidian Violet Django admin
│   ├── utils.py             ← Grade engine, SGPA/CGPA, PDF, email, Excel
│   │
│   ├── templatetags/
│   │   └── acadivo_tags.py  ← grade_badge, get_item, elective_selected, cgpa_color
│   │
│   ├── templates/results/
│   │   ├── base.html                ← Sidebar, particles, intro loader
│   │   ├── login.html               ← Standalone login (no sidebar)
│   │   ├── admin_dashboard.html     ← Stats, top performers, batch progress
│   │   ├── student_list.html        ← Search + filter + CGPA colour
│   │   ├── student_form.html        ← Add / Edit student
│   │   ├── subject_list.html        ← Grouped by semester
│   │   ├── subject_form.html        ← Add / Edit subject
│   │   ├── elective_select.html     ← Per-batch elective picker
│   │   ├── marks_entry.html         ← Live grade calc on keypress
│   │   ├── marks_upload.html        ← Drag-drop CSV/Excel, error table
│   │   ├── result_preview.html      ← SGPA review before publish
│   │   ├── result_publish.html      ← Confirm checkbox + email trigger
│   │   ├── student_dashboard.html   ← CGPA count-up, Chart.js SGPA trend
│   │   ├── student_result.html      ← Full marks table, sem switcher
│   │   └── marksheet_list.html      ← PDF download cards
│   │
│   ├── static/results/
│   │   ├── css/acadivo.css          ← Obsidian Violet design system
│   │   ├── css/admin_theme.css      ← Django admin dark theme
│   │   └── js/acadivo.js            ← Particles, 3D tilt, scroll reveal, count-up
│   │
│   ├── fixtures/
│   │   ├── subjects.json            ← 65 NEP BSc CS subjects (Sem 1–6)
│   │   └── demo_data.json           ← Demo marks + published results
│   │
│   └── management/commands/
│       └── setup_demo.py            ← One command: create all accounts + load data
│
├── manage.py
├── requirements.txt
├── .env                             ← Environment variables (SECRET_KEY, email)
└── README.md
```

---

## Features

### Admin Portal
| Feature | Details |
|---|---|
| Dashboard | Stat cards (count-up), top performers, batch result progress |
| Student Management | Add/edit/deactivate, roll number validation, password confirm |
| Subject Management | 65 NEP subjects pre-loaded, grouped by semester |
| Elective Selection | Admin picks one elective per group per batch |
| Mark Entry | Live CE+ESE → grade badge update on keypress, prev/next student nav |
| CSV Upload | Drag-drop upload, per-row error reporting |
| Excel Template | Styled `.xlsx` download — violet headers, subject columns, freeze panes |
| Result Preview | SGPA table, pass/fail, expandable subject detail rows |
| Result Publish | Confirm checkbox, double-submit prevention, auto email + CGPA recalc |

### Student Portal
| Feature | Details |
|---|---|
| Dashboard | CGPA count-up from 0, Chart.js SGPA trend line, semester status grid |
| My Results | Sem switcher tabs, full marks table, 4-card summary strip |
| Marksheets | Download PDF for each published semester |
| PDF Marksheet | A4 portrait, dark header, colour-coded grade table, result strip |

### UI — Obsidian Violet Glowed
- Background `#100D1A` / `#1A1628` · Accent `#9D6FFF` / `#BFA3FF`
- Intro loader with progress bar · 3D depth particle system (z-parallax)
- 3D card tilt: `perspective(1400px) rotateY(4deg)` · `0.22s ease-out`
- Scroll reveal via IntersectionObserver · count-up animations
- Fonts: Inter 800 (display) + IBM Plex Mono 400/500

---

## Grading Scale — NEP Mumbai University (10-point)

| Percentage | Grade | Grade Points | Class          |
|-----------|-------|-------------|----------------|
| 90–100    | O     | 10          | Outstanding    |
| 75–89     | A+    | 9           | Excellent      |
| 65–74     | A     | 8           | Very Good      |
| 55–64     | B+    | 7           | Good           |
| 50–54     | B     | 6           | Above Average  |
| 40–49     | C     | 5           | Average / Pass |
| < 40      | F     | 0           | Fail           |

**CE** (Internal) 20 marks + **ESE** (Exam) 30 marks = **50 marks** per subject
**SGPA** = Σ(GP × Credits) ÷ Σ(Credits)
**CGPA** = Average of all published semester SGPAs

---

## Email Setup (Optional)

1. Enable 2-Factor Authentication on your Gmail account
2. Go to **Google Account → Security → App Passwords**
3. Generate a 16-character app password
4. Edit `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_FROM_EMAIL=Acadivo <noreply@acadivo.com>
```

By default (dev mode) emails print to the terminal — no Gmail setup needed.

---

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Django 4.2 (Python)                             |
| Database  | SQLite (zero setup, file-based)                 |
| Frontend  | Custom CSS (Obsidian Violet) + Vanilla JS       |
| Charts    | Chart.js via CDN                                |
| PDF       | ReportLab 4.x                                   |
| Excel     | openpyxl 3.x                                    |
| Email     | Django + Gmail SMTP                             |
| Fonts     | Inter + IBM Plex Mono (Google Fonts)            |

---

*Acadivo — Built for Anjuman Islam Janjira Degree College of Science*
*BSc CS (NEP) · Mumbai University · Academic Year 2025–26*
