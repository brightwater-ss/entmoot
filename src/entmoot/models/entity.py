from pydantic import BaseModel

from .fact import FactGroup


class EntitySummary(BaseModel):
    id: str
    name: str
    aliases: list[str]
    domains: list[str]


class EntityResponse(BaseModel):
    id: str
    name: str
    aliases: list[str]
    domains: list[str]
    claimed_by: str | None
    merged_into: str | None
    created_at: str
    updated_at: str


class EntityWithFacts(EntityResponse):
    fact_groups: list[FactGroup]
