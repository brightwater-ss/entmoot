from pydantic import BaseModel, Field

from .fact import SourceType


class CreateDomainRequest(BaseModel):
    name: str
    slug: str
    parent_slug: str | None = None


class CreateEntityRequest(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    domain_slugs: list[str] = Field(default_factory=list)


class CreateAttributeRequest(BaseModel):
    name: str
    description: str | None = None
    unit: str | None = None
    domain_slugs: list[str] = Field(default_factory=list)


class CreateFactRequest(BaseModel):
    entity_id: str
    attribute_id: str
    value: str
    source_type: SourceType = "admin"
    source_url: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
