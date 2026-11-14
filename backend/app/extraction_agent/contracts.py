"""Strict source-table contract; model responses contain transcriptions, not arithmetic."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Statement = Literal['income_statement', 'balance_sheet', 'cash_flow']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Column(Strict):
    period: str = Field(pattern=r'^20\d{2}$')
    scope: str = Field(min_length=1, max_length=80)


class Row(Strict):
    label: str = Field(min_length=1, max_length=300)
    note: str = Field(default='', max_length=30)
    values: list[str] = Field(min_length=1, max_length=12)
    quote: str = Field(min_length=1, max_length=4000)


class Table(Strict):
    statement: Statement
    evidence_id: str
    columns: list[Column] = Field(min_length=1, max_length=12)
    header_quote: str = Field(min_length=1, max_length=1000)
    scope_quote: str = Field(min_length=1, max_length=1000)
    unit_quote: str = Field(min_length=1, max_length=300)
    unit: str
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    currency_evidence_id: str
    currency_quote: str = Field(min_length=1, max_length=1000)
    rows: list[Row] = Field(max_length=500)


class Extraction(Strict):
    tables: list[Table] = Field(max_length=40)


class Account(Strict):
    statement: Statement
    aliases: list[str] = Field(min_length=1)
    required: bool = True


class Equation(Strict):
    id: str
    terms: dict[str, int]
    tolerance: str = Field(default='0', pattern=r'^\d+(\.\d+)?$')
    required: bool = True


class SpreadProfile(Strict):
    version: str
    borrower_types: list[str] = Field(min_length=1)
    scopes: list[str] = Field(min_length=1)
    readiness_scope: str
    units: dict[str, str]
    currencies: dict[str, list[str]]
    accounts: dict[str, Account]
    equations: list[Equation]

    # Validation here keeps malformed configuration out of case snapshots.
    @classmethod
    def validate_profile(cls, profile):
        from decimal import Decimal, InvalidOperation
        if profile.readiness_scope not in profile.scopes:
            raise ValueError('Readiness scope must be configured')
        if not profile.accounts or not profile.equations:
            raise ValueError('Spread profile requires accounts and equations')
        try:
            valid_units = bool(profile.units) and all(len(v) <= 30 and Decimal(v).is_finite()
                and Decimal('1e-12') <= Decimal(v) <= Decimal('1e12') for v in profile.units.values())
        except InvalidOperation:
            valid_units = False
        if not valid_units:
            raise ValueError('Spread unit scales must be positive finite decimals within supported precision')
        seen = set()
        for account in profile.accounts.values():
            for alias in account.aliases:
                key = (account.statement, ' '.join(alias.casefold().split()))
                if key in seen:
                    raise ValueError('Ambiguous spread account alias')
                seen.add(key)
        if len({e.id for e in profile.equations}) != len(profile.equations):
            raise ValueError('Duplicate spread equation')
        for equation in profile.equations:
            if (not equation.terms or not set(equation.terms) <= profile.accounts.keys()
                    or any(type(v) is not int or v not in {-1, 1} for v in equation.terms.values())):
                raise ValueError('Invalid spread equation terms')
        return profile
