from pydantic import BaseModel


class AttributeSummary(BaseModel):
    id: str
    name: str
    domain: str | None = None


class AttributeResponse(BaseModel):
    id: str
    name: str
    description: str | None
    unit: str | None
    domains: list[str]
    created_at: str
