from pydantic import BaseModel

from .value import ValueGroup


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
    value_groups: list[ValueGroup]
