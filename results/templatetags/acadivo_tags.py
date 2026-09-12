"""
Acadivo — Custom Template Tags & Filters
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Usage: {{ my_dict|get_item:key }}"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def mul(value, arg):
    """Multiply: {{ value|mul:arg }}"""
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage: {{ value|percentage:total }}"""
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def grade_badge(grade):
    """Return CSS class for a grade letter."""
    mapping = {
        'O':  'badge-O',
        'A+': 'badge-Ap',
        'A':  'badge-A',
        'B+': 'badge-Bp',
        'B':  'badge-B',
        'C':  'badge-C',
        'F':  'badge-F',
    }
    return mapping.get(grade, 'badge-F')


@register.filter
def cgpa_color(cgpa):
    """Return inline color style for CGPA value."""
    try:
        v = float(cgpa)
        if v >= 9:
            return 'color:var(--green);text-shadow:0 0 10px rgba(52,211,153,0.4)'
        if v >= 7:
            return 'color:var(--accent2)'
        if v >= 5:
            return 'color:var(--amber)'
        return 'color:var(--red)'
    except (TypeError, ValueError):
        return 'color:var(--muted)'


@register.simple_tag
def elective_selected(current_dict, batch_id, semester, group):
    """
    Returns the selected SemesterElective object for a given
    batch/semester/elective_group combination, or None.
    Usage: {% elective_selected current batch.pk sem group as sel %}
    Keys in current_dict are (int batch_id, int semester, str group).
    """
    try:
        return current_dict.get((int(batch_id), int(semester), str(group)))
    except (TypeError, ValueError):
        return None
