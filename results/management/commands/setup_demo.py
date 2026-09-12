"""
Acadivo Management Command — setup_demo
Creates superuser + 3 demo student accounts (one per batch).

Usage:
  python manage.py setup_demo

Creates:
  Admin   → username: admin     / password: admin@acadivo
  FY Demo → username: 2026001   / password: student@acadivo
  SY Demo → username: 2025001   / password: student@acadivo
  TY Demo → username: 2024001   / password: student@acadivo
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from results.models import Batch, Student


class Command(BaseCommand):
    help = 'Create superuser + demo student accounts for Acadivo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recreate accounts even if they already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write(self.style.MIGRATE_HEADING('\n🚀 Acadivo Demo Setup\n'))

        # ── 1. Superuser (Admin) ──────────────────────────────
        self._create_superuser(force)

        # ── 2. Demo Students ──────────────────────────────────
        demo_students = [
            {'roll': '2026001', 'name': 'Zain Datey',    'batch': 'FY', 'email': 'zain@acadivo.demo'},
            {'roll': '2025001', 'name': 'Rohit Shaikh',  'batch': 'SY', 'email': 'rohit@acadivo.demo'},
            {'roll': '2024001', 'name': 'Priya Khan',    'batch': 'TY', 'email': 'priya@acadivo.demo'},
        ]

        for s in demo_students:
            self._create_student(s, force)

        self.stdout.write('\n' + self.style.SUCCESS('✅ Setup complete!\n'))
        self.stdout.write(self.style.WARNING('Login credentials:'))
        self.stdout.write('  Admin   → admin / admin@acadivo')
        self.stdout.write('  Students → <roll_number> / student@acadivo')
        self.stdout.write('\n  ⚠️  Change passwords before deploying!\n')

    # ────────────────────────────────────────────────────────
    def _create_superuser(self, force):
        username = 'admin'
        password = 'admin@acadivo'

        if User.objects.filter(username=username).exists():
            if force:
                User.objects.filter(username=username).delete()
                self.stdout.write(f'  Deleted existing superuser: {username}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⏭  Admin "{username}" already exists — skipping')
                )
                return

        User.objects.create_superuser(
            username=username,
            email='admin@acadivo.com',
            password=password,
            first_name='Acadivo',
            last_name='Admin',
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Superuser created: {username}'))

    # ────────────────────────────────────────────────────────
    def _create_student(self, data, force):
        roll   = data['roll']
        name   = data['name']
        batch_name = data['batch']
        email  = data['email']
        password = 'student@acadivo'

        # Skip if exists and not forced
        if Student.objects.filter(roll_number=roll).exists():
            if force:
                # Delete Student first (cascades to User)
                student = Student.objects.get(roll_number=roll)
                student.user.delete()
                self.stdout.write(f'  Deleted existing student: {roll}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⏭  Student "{roll}" already exists — skipping')
                )
                return

        # Get batch
        try:
            batch = Batch.objects.get(name=batch_name)
        except Batch.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'  ✗ Batch "{batch_name}" not found. '
                    f'Run: python manage.py loaddata results/fixtures/subjects.json'
                )
            )
            return

        # Create Django User
        user = User.objects.create_user(
            username=roll,
            email=email,
            password=password,
            first_name=name.split()[0],
            last_name=' '.join(name.split()[1:]),
            is_staff=False,
            is_superuser=False,
        )

        # Create Student profile
        Student.objects.create(
            user=user,
            roll_number=roll,
            full_name=name,
            email=email,
            batch=batch,
        )

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Student created: {name} ({roll}) — {batch_name}')
        )

    def _load_demo_data(self):
        """Load demo marks, SGPA and CGPA data fixture."""
        import os
        from django.core import management
        fixture = os.path.join(
            os.path.dirname(__file__), '..', '..', 'fixtures', 'demo_data.json'
        )
        if os.path.exists(os.path.normpath(fixture)):
            try:
                management.call_command(
                    'loaddata', 'results/fixtures/demo_data.json',
                    verbosity=0
                )
                self.stdout.write(self.style.SUCCESS('  ✓ Demo marks and results loaded'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ Could not load demo data: {e}'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ demo_data.json not found — skipping'))
