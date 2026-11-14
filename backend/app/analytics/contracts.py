"""Explicit reviewed source mappings. Numeric values are read from evidence, not requests."""
from datetime import date
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Binding(Strict):
    evidence_id: str
    quote: str = Field(min_length=1, max_length=10000)
    token: str = Field(min_length=1, max_length=100)
    # Repeated equal tokens are disambiguated by their zero-based occurrence.
    occurrence: int = Field(default=0, ge=0, le=100)
    unit: Literal['currency', 'currency_thousand', 'currency_million', 'currency/unit',
                  'cents/unit', 'units', 'percent', 'fraction', 'times', 'years', 'sqm']
    currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    period: str = Field(min_length=1, max_length=80)
    scope: str = Field(min_length=1, max_length=200)
    basis: str = Field(min_length=1, max_length=100)
    context_quote: str = Field(min_length=1, max_length=10000)
    proxy: bool = False
    item: str | None = None
    maturity: date | None = None


class MetricInputs(Strict):
    bindings: dict[str, Annotated[list[Binding], Field(max_length=200)]] = Field(default_factory=dict, max_length=20)
    spread_value_ids: dict[str, Annotated[list[str], Field(max_length=200)]] = Field(default_factory=dict, max_length=20)

    @model_validator(mode='after')
    def unique_operands(self):
        if self.bindings.keys() & self.spread_value_ids.keys():
            raise ValueError('An operand cannot mix reported and spread mappings')
        return self


class TableInput(Strict):
    kind: Literal['exposure', 'covenants', 'conduct', 'projections']
    evidence_ids: list[str] = Field(min_length=1, max_length=10)


class AnalyticsRequest(Strict):
    set_id: str = 'reit'
    period: str = Field(min_length=1, max_length=80)
    scope: str = Field(min_length=1, max_length=200)
    reviewed_by: str = Field(min_length=1, max_length=100)
    review_note: str = Field(min_length=1, max_length=1000)
    metrics: dict[str, MetricInputs] = Field(default_factory=dict, max_length=100)
    tables: list[TableInput] = Field(default_factory=list, max_length=10)
