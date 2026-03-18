from litestar import Litestar, get
from litestar.datastructures import State

from entmoot.graph import close_driver, init_driver, init_schema
from entmoot.routes import AdminController, AttributeController, EntityController


@get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(connect_db: bool = True) -> Litestar:
    async def on_startup(app: Litestar) -> None:
        driver = await init_driver()
        await init_schema(driver)
        app.state.neo4j = driver

    async def on_shutdown(app: Litestar) -> None:
        await close_driver()

    return Litestar(
        route_handlers=[health, EntityController, AttributeController, AdminController],
        on_startup=[on_startup] if connect_db else [],
        on_shutdown=[on_shutdown] if connect_db else [],
        state=State({}),
    )


app = create_app()
