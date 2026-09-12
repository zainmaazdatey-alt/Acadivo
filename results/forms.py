"""
Acadivo — Forms
Step 4: StudentForm with roll number validation.
"""

import re
from django import forms
from django.contrib.auth.models import User
from .models import Student, Batch


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Roll Number',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••••',
        }),
    )


class StudentForm(forms.ModelForm):
    """
    Used for both Add and Edit student.
    - roll_number is read-only on edit (set via __init__)
    - password is required on Add, optional on Edit
    """
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep existing password',
        }),
        help_text='Minimum 8 characters.',
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password',
        }),
    )

    class Meta:
        model  = Student
        fields = ['roll_number', 'full_name', 'email', 'phone', 'batch']
        widgets = {
            'roll_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2026001',
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name as per university record',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@email.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '10-digit mobile number',
            }),
            'batch': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'roll_number': 'Roll Number',
            'full_name':   'Full Name',
            'email':       'Email Address',
            'phone':       'Phone Number',
            'batch':       'Batch (Year)',
        }
        help_texts = {
            'roll_number': 'Format: 4-digit year + 3-digit serial (e.g. 2026001). '
                           'This becomes the student\'s login username.',
        }

    def __init__(self, *args, **kwargs):
        self.instance_pk = kwargs.get('instance') and kwargs['instance'].pk
        super().__init__(*args, **kwargs)

        # Roll number is not editable after creation
        if self.instance_pk:
            self.fields['roll_number'].disabled = True
            self.fields['roll_number'].help_text = 'Roll number cannot be changed after creation.'
            self.fields['password'].help_text    = 'Leave blank to keep the current password.'
        else:
            # Password required for new students
            self.fields['password'].required         = True
            self.fields['confirm_password'].required = True
            self.fields['password'].help_text        = 'Minimum 8 characters.'

    def clean_roll_number(self):
        roll = self.cleaned_data.get('roll_number', '')
        if not re.match(r'^\d{7}$', str(roll)):
            raise forms.ValidationError(
                'Roll number must be exactly 7 digits: 4-digit year + 3-digit serial (e.g. 2026001).'
            )
        # Check uniqueness (skip on edit since field is disabled)
        if not self.instance_pk:
            if User.objects.filter(username=roll).exists():
                raise forms.ValidationError(
                    f'Roll number {roll} is already registered.'
                )
        return roll

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError('Phone must be exactly 10 digits.')
        return phone

    def clean(self):
        cleaned = super().clean()
        pw  = cleaned.get('password', '').strip()
        pw2 = cleaned.get('confirm_password', '').strip()

        if pw or not self.instance_pk:
            if len(pw) < 8:
                self.add_error('password', 'Password must be at least 8 characters.')
            if pw != pw2:
                self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned


class SubjectForm(forms.ModelForm):
    """Used for Add and Edit subject."""
    class Meta:
        from results.models import Subject
        model  = Subject
        fields = [
            'semester', 'code', 'name', 'subject_type', 'group',
            'credits', 'ce_max', 'ese_max',
            'is_elective', 'elective_group', 'order', 'is_active',
        ]
        widgets = {
            'semester':      forms.Select(attrs={'class': 'form-select'}),
            'code':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1101111'}),
            'name':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject name'}),
            'subject_type':  forms.Select(attrs={'class': 'form-select'}),
            'group':         forms.Select(attrs={'class': 'form-select'}),
            'credits':       forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'ce_max':        forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 20}),
            'ese_max':       forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 30}),
            'is_elective':   forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'elective_group':forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MJEL_S5'}),
            'order':         forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'ce_max':         'CE Max Marks (Internal)',
            'ese_max':        'ESE Max Marks (Exam)',
            'is_elective':    'Is Elective Subject',
            'elective_group': 'Elective Group Code',
            'order':          'Display Order',
            'is_active':      'Active',
        }
        help_texts = {
            'elective_group': 'e.g. MJEL_S5 — subjects with same group are mutually exclusive choices.',
            'order':          'Lower number appears first in the subject list.',
        }

    def clean(self):
        cleaned = super().clean()
        is_elective    = cleaned.get('is_elective', False)
        elective_group = cleaned.get('elective_group', '').strip()
        if is_elective and not elective_group:
            self.add_error('elective_group', 'Elective group code is required when subject is marked as elective.')
        return cleaned
