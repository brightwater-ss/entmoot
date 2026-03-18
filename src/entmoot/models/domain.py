from pydantic import BaseModel


class DomainResponse(BaseModel):
    id: str
    name: str
    slug: str
