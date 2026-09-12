"""
Acadivo — Django Settings
BSc CS Result Portal | Anjuman Islam Janjira Degree College of Science
NEP Mumbai University | Obsidian Violet UI
"""

from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ────────────────────────────────────────────
SECRET_KEY = config(
    'SECRET_KEY',
    default='acadivo-dev-secret-key-change-this-in-production-!@#$%'
)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [h.strip() for h in v.split(',')]
)

# ─── APPLICATIONS ─────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Acadivo app
    'results',
]

# ─── MIDDLEWARE ────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acadivo.urls'

# ─── TEMPLATES ────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Project-level templates (admin overrides live here)
        'DIRS': [BASE_DIR / 'results' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'acadivo.wsgi.application'

# ─── DATABASE — SQLite (zero setup, free) ─────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ─── AUTHENTICATION ───────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom login URL — Acadivo login page
LOGIN_URL          = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ─── INTERNATIONALISATION ─────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

# ─── STATIC FILES ─────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # for collectstatic in production

# ─── MEDIA FILES (college logo, etc.) ─────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── DEFAULT PRIMARY KEY ──────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── EMAIL — Gmail SMTP (free) ────────────────────────────
# To activate: set these in .env file
# EMAIL_HOST_USER=your_gmail@gmail.com
# EMAIL_HOST_PASSWORD=your_16char_app_password
EMAIL_BACKEND       = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='Acadivo <noreply@acadivo.com>')

# ─── SESSION ──────────────────────────────────────────────
SESSION_COOKIE_AGE      = 86400   # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ─── ACADIVO CUSTOM SETTINGS ─────────────────────────────
COLLEGE_NAME     = 'Anjuman Islam Janjira Degree College of Science'
COLLEGE_LOCATION = 'Murud-Janjira, Raigad District, Maharashtra'
COLLEGE_AFF      = 'Affiliated to University of Mumbai'
COLLEGE_PROGRAM  = 'BSc Computer Science (NEP)'
ACADEMIC_YEAR    = '2025-26'

# Grading scale — NEP Mumbai University 10-point
GRADE_SCALE = [
    (90,  'O',  10, 'Outstanding'),
    (75,  'A+',  9, 'Excellent'),
    (65,  'A',   8, 'Very Good'),
    (55,  'B+',  7, 'Good'),
    (50,  'B',   6, 'Above Average'),
    (40,  'C',   5, 'Average / Pass'),
    (0,   'F',   0, 'Fail'),
]

# Marking scheme
THEORY_CE_MAX    = 20
THEORY_ESE_MAX   = 30
PRACTICAL_CE_MAX = 20
PRACTICAL_ESE_MAX= 30
SUBJECT_TOTAL    = 50
PASS_PERCENTAGE  = 40   # minimum 40% to pass

# Roll number validation pattern: 4-digit year + 3-digit serial
# e.g. 2026001, 2026042
ROLL_NUMBER_PATTERN = r'^\d{4}\d{3}$'
