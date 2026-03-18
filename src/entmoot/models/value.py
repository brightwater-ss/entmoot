from typing import Literal

from pydantic import BaseModel

SourceType = Literal["org-verified", "admin", "scraped", "ai-extracted", "manual"]

# Trust tier order — lower index = higher trust
SOURCE_TYPE_ORDER: list[SourceType] = [
    "org-verified",
    "admin",
    "scraped",
    "ai-extracted",
    "manual",
]


class ValueResponse(BaseModel):
    id: str
    value: str
    source_type: SourceType
    source_url: str | None
    confidence: float
    org_id: str | None
    contributed_at: str
    conflict: bool


class ValueGroup(BaseModel):
    """All values for a single (entity, attribute) pair, ordered by trust tier."""

    attribute_id: str
    attribute_name: str
    values: list[ValueResponse]
    conflict: bool
