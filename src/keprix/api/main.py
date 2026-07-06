"""FastAPI application entrypoint."""

from keprix.api.server import create_app

app = create_app()
