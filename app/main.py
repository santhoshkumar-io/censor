import os

from fastapi import FastAPI, Request, UploadFile
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import get_scalar_api_reference
from app.audio_censor import AudioCensor
app = FastAPI(docs_url=None, redoc_url=None, title="Audio Censor API", version="0.1.0")
ac = AudioCensor()
UPLOADS = "uploads"
os.makedirs(UPLOADS, exist_ok=True)

def save_file(upload_file: UploadFile, destination: str) -> None:
    """Save an uploaded file to the given destination path."""
    with open(destination, "wb") as f:
        f.write(upload_file.file.read())

app.mount(f"/{UPLOADS}", StaticFiles(directory=UPLOADS), name=UPLOADS)


@app.post("/censor-audio")
async def censor_audio(audio_file: UploadFile, request: Request):
    file_path = f"{UPLOADS}/{audio_file.filename}"
    # Save the upload first: transcribe_audio reads the file from disk.
    save_file(audio_file, file_path)

    words = ac.transcribe_audio(file_path)

    output_name = f"censored_{audio_file.filename}"
    output_path = f"{UPLOADS}/{output_name}"
    ac.mute_audio(
        input_path=file_path,
        output_path=output_path,
        words=ac.profanity_check(words["word_segments"]),
    )
    return {
        "message": "Audio censored",
        "url": str(request.url_for(UPLOADS, path=output_name)),
    }


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
    )
