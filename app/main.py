from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import get_scalar_api_reference

from app.api.router import router
from app.database.session import db_init, engine
from app.utils import UPLOADS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, before it accepts requests.
    await db_init()
    yield
    # Close pooled DB connections on shutdown.
    await engine.dispose()


app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="Audio Censor API",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount(f"/{UPLOADS}", StaticFiles(directory=UPLOADS), name=UPLOADS)
app.include_router(router)


def custom_openapi() -> dict:
    """Add ``format: binary`` to file fields so Scalar shows a file picker.

    FastAPI marks uploads only with ``contentMediaType`` (OpenAPI 3.1), which
    Scalar renders as a plain text input.
    """
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title, version=app.version, routes=app.routes
    )
    for component in schema.get("components", {}).get("schemas", {}).values():
        for prop in component.get("properties", {}).values():
            if prop.get("contentMediaType") == "application/octet-stream":
                prop["format"] = "binary"
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/docs", include_in_schema=False)
async def scalar_docs() -> HTMLResponse:
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Scalar",
        # Pre-select the OAuth2 password login in the Auth panel, so "Authorize"
        # calls /token and attaches the bearer token to every request.
        authentication={"preferredSecurityScheme": "OAuth2PasswordBearer"},
        # Keep the token in the browser across reloads (dev docs convenience).
        persist_auth=True,
    )
