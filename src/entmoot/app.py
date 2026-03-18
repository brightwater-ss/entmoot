from litestar import Litestar, get
from litestar.datastructures import State

from entmoot.graph import close_driver, init_driver, init_schema
from entmoot.routes import AttributeController, EntityController


@get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def on_startup(app: Litestar) -> None:
    driver = await init_driver()
    await init_schema(driver)
    app.state.neo4j = driver


async def on_shutdown(app: Litestar) -> None:
    await close_driver()


app = Litestar(
    route_handlers=[health, EntityController, AttributeController],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    state=State({}),
)
