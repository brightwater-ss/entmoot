from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers import BaseRouteHandler

from entmoot.config import settings


def admin_guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Require X-Admin-Key header matching ADMIN_API_KEY in env."""
    api_key = connection.headers.get("x-admin-key")
    if not api_key or api_key != settings.admin_api_key:
        raise NotAuthorizedException(detail="Valid X-Admin-Key header required")
