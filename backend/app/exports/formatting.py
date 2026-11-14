"""Display-only credit-paper formatting; never changes saved numeric values."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re


def number(value, unit='currency_million'):
    places = 1 if unit in {'percent', 'percentage points', 'years'} else 0 if unit in {'count', 'days'} else 2
    return format(Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), f'.{places}f')


def prose(text):
    # Unit-bound tokens only: dates, IDs, citations and unlabelled quantities stay intact.
    text = re.sub(r'(-?\d+(?:\.\d+)?)(?=%| percentage points| percent\b)', lambda m: number(m[0], 'percent'), text)
    text = re.sub(r'(-?\d+(?:\.\d+)?)(?=x\b| times\b)', lambda m: number(m[0], 'times'), text)
    return re.sub(r'(SGD )(-?\d+(?:\.\d+)?)(?= million|m\b)', lambda m: m[1] + number(m[2]), text)


def human_date(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%d %b %Y').lstrip('0')
