"""Figure handling for the specification-driven ES. All arithmetic and unit conversion happens here, in Decimal."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import ast
import re
import unicodedata

SCALES = {'unit': Decimal(1), 'thousand': Decimal(1000), 'million': Decimal(1_000_000), 'billion': Decimal(1_000_000_000)}
TOKEN = re.compile(r'\d[\d,]*(?:\.\d+)?')


def squash(text):
    return re.sub(r'\s+', ' ', str(text)).strip()


def canon(text):
    """Text for comparing a quoted line with a page: typographic quotes and dashes, case and spacing do not count."""
    text = unicodedata.normalize('NFKC', str(text))
    for old, new in (('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('–', '-'), ('—', '-'), ('−', '-'), ('\u00ad', '')):
        text = text.replace(old, new)
    return re.sub(r'\s+', '', text).lower()


def parse_printed(raw):
    """A figure as printed in a source: '1,234.5', '(1,234)', '-12.3', '43.4%'. Returns Decimal or None."""
    text = str(raw).strip().replace('%', '').replace('x', '').strip()
    negative = text.startswith('(') and text.endswith(')') or text.startswith('-') or text.startswith('−')
    digits = TOKEN.search(text)
    if not digits:
        return None
    try:
        value = Decimal(digits.group().replace(',', ''))
    except InvalidOperation:
        return None
    return -value if negative else value


def figure_in(raw, text):
    """True when the printed figure appears in the text, comparing digits with thousands separators removed."""
    digits = TOKEN.search(str(raw))
    if not digits:
        return False
    wanted = Decimal(digits.group().replace(',', ''))
    return any(Decimal(token.replace(',', '')) == wanted for token in TOKEN.findall(text))


def unsupported_figures(text, allowed_text):
    """Figures in drafted wording that do not appear in the cited evidence. Years and small counts are not figures."""
    # Compared by value, so 50 matches 50.0 and 1,200 matches 1200. No rounding: 85.2 does not match 85.0.
    known = {Decimal(token.replace(',', '')) for token in TOKEN.findall(allowed_text)}
    missing = []
    for token in TOKEN.findall(text):
        plain = token.replace(',', '')
        if Decimal(plain) in known:
            continue
        if re.fullmatch(r'(19|20)\d\d', plain) or (plain.isdigit() and int(plain) <= 31):
            continue
        missing.append(token)
    return missing


def fmt(value, kind='number', places=None):
    if value is None:
        return ''
    if places is None:
        places = 0 if kind == 'amount' else 1 if kind == 'percent' else 2
    quantum = Decimal(1).scaleb(-places)
    return format(Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP), f',.{places}f')


def evaluate(expression, values, names=None):
    """Evaluate + - * / over named Decimal values (names may contain spaces). Returns None if any operand is missing.
    `names` lists every name the expression may use, so a name without a value reads as missing."""
    names = sorted(set(names or []) | set(values), key=len, reverse=True)
    source = expression
    for i, name in enumerate(names):
        source = source.replace(name, f'v{i}_')
    env = {f'v{i}_': values.get(name) for i, name in enumerate(names)}

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left), visit(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Div):
                return None if right == 0 else left / right
            return left + right if isinstance(node.op, ast.Add) else left - right if isinstance(node.op, ast.Sub) else left * right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = visit(node.operand)
            return None if inner is None else -inner
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        raise ValueError('Unsupported expression')
    return visit(ast.parse(source, mode='eval'))
