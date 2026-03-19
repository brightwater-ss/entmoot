import re

from pydantic import BaseModel, Field, field_validator, model_validator

from .value import SourceType


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


class CreateValueRequest(BaseModel):
    entity_id: str
    attribute_id: str
    value: str
    source_type: SourceType = "admin"
    source_url: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


_Q_RE = re.compile(r"^Q\d+$")
_P_RE = re.compile(r"^P\d+$")


class WikidataImportRequest(BaseModel):
    class_ids: list[str] = Field(default_factory=list, description="Wikidata class Q-IDs")
    item_ids: list[str] = Field(default_factory=list, description="Explicit item Q-IDs")
    property_ids: list[str] = Field(default_factory=list, description="Property P-IDs to import as values")
    domain_slugs: list[str] = Field(default_factory=list, description="Entmoot domain slugs to link entities to")

    @field_validator("class_ids", "item_ids", mode="before")
    @classmethod
    def validate_q_ids(cls, v: list[str]) -> list[str]:
        for item in v:
            if not _Q_RE.match(item):
                raise ValueError(f"Invalid Wikidata Q-ID: {item!r} (expected format: Q<digits>)")
        return v

    @field_validator("property_ids", mode="before")
    @classmethod
    def validate_p_ids(cls, v: list[str]) -> list[str]:
        for item in v:
            if not _P_RE.match(item):
                raise ValueError(f"Invalid Wikidata P-ID: {item!r} (expected format: P<digits>)")
        return v

    @model_validator(mode="after")
    def at_least_one_source(self) -> "WikidataImportRequest":
        if not self.class_ids and not self.item_ids:
            raise ValueError("Provide at least one of class_ids or item_ids")
        return self


class WikidataImportResult(BaseModel):
    entities_created: int = 0
    entities_skipped: int = 0
    attributes_created: int = 0
    attributes_skipped: int = 0
    values_created: int = 0
    errors: list[str] = Field(default_factory=list)
