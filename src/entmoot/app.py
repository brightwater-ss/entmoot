from litestar import Litestar, get


@get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app = Litestar(route_handlers=[health])
