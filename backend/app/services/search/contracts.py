"""Public-only search contracts. Evidence content is never a query or instruction."""
from datetime import datetime
from hashlib import sha256
import ipaddress
import re
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...schemas import utcnow
from ..intake import MAX_BYTES, normalize


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class PublicIdentity(Strict):
    name: str = Field(min_length=1, max_length=300)
    sgx_code: str | None = Field(default=None, pattern=r'^[A-Za-z0-9]{1,12}$')
    isin: str | None = Field(default=None, pattern=r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
    lei: str | None = Field(default=None, pattern=r'^[A-Z0-9]{20}$')

    @model_validator(mode='after')
    def public_name(self):
        if not self.name.strip() or any(ord(c) < 32 for c in self.name):
            raise ValueError('Public name must be nonblank and on one line')
        return self

    @classmethod
    def from_case(cls, case):
        # Never copy arbitrary identifiers, facility fields, CA position or text.
        return cls(name=case.borrower_name, **{k: v for k, v in case.public_identifiers.items()
                                             if k in {'sgx_code', 'isin', 'lei'}})

    @property
    def query(self):
        return ' '.join([self.name, *[v for k, v in self.model_dump().items() if k != 'name' and v]])


def public_url(url):
    """Validate provenance URLs without DNS/network. No result URL is fetched.

    A future direct fetcher must resolve/check all IPs, pin its connection and
    revalidate every redirect. A syntactically public hostname alone is NOT a
    safe network destination.
    """
    if len(url) > 4096 or any(c.isspace() or ord(c) < 32 for c in url) or '\\' in url:
        raise ValueError('Invalid public URL')
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower().rstrip('.')
        if (parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password
                or parsed.port not in {None, 80, 443} or not host):
            raise ValueError('Public HTTP(S) URL required')
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if ('.' not in host or host.endswith(('.localhost', '.local', '.internal', '.test', '.invalid'))
                    or not re.fullmatch(r'[a-z0-9.-]+', host)
                    or re.fullmatch(r'[0-9.x]+', host)):
                raise ValueError('Local/non-public URL rejected')
        else:
            if not address.is_global:
                raise ValueError('Local/non-public URL rejected')
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid or non-public URL') from error
    return url


class SupportMapping(Strict):
    id: int = Field(ge=1)
    coverage: Literal['full', 'partial']
    pages: list[int] = Field(min_length=1)


class PublicResult(Strict):
    title: str = Field(min_length=1, max_length=500)
    url: str
    retrieved_at: datetime
    entity: str
    period: str
    filename: str
    content: bytes = Field(min_length=1, max_length=MAX_BYTES, repr=False, exclude=True)
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    media_type: Literal['application/pdf', 'text/plain']
    catalogue_id: int | None = None
    suggestion_id: str | None = None
    coverage: Literal['full', 'partial'] = 'full'
    scope: str
    catalogue_support: list[SupportMapping] = Field(default_factory=list)
    page_references: list[dict] = Field(default_factory=list)
    cached: bool = False
    source_id: str

    @model_validator(mode='after')
    def validate_source(self):
        public_url(self.url)
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset().total_seconds() != 0:
            raise ValueError('Retrieval date must be UTC')
        if sha256(self.content).hexdigest() != self.content_hash:
            raise ValueError('Public content hash mismatch')
        if (self.catalogue_id is None) == (self.suggestion_id is None):
            raise ValueError('Result needs one public catalogue or suggestion mapping')
        return self


class SearchResult(Strict):
    outcome: Literal['not run', 'failed', 'no match', 'found']
    results: list[PublicResult] = Field(default_factory=list)
    reason: str
    attempted_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode='after')
    def matching_outcome(self):
        if bool(self.results) != (self.outcome == 'found'):
            raise ValueError('Only found outcomes carry results')
        return self


class SearchProvider(Protocol):
    name: str

    def search(self, public_identity: PublicIdentity) -> SearchResult: ...


def entity_matches(identity, entity):
    return normalize(identity.name) == normalize(entity)
