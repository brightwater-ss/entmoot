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


class FactResponse(BaseModel):
    id: str
    value: str
    source_type: SourceType
    source_url: str | None
    confidence: float
    org_id: str | None
    contributed_at: str
    conflict: bool


class FactGroup(BaseModel):
    """All facts for a single (entity, attribute) pair, ordered by trust tier."""

    attribute_id: str
    attribute_name: str
    facts: list[FactResponse]
    conflict: bool
