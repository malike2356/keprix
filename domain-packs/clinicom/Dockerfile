FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 sidecar
COPY --chown=sidecar:sidecar . /app
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic
USER sidecar
EXPOSE 3353
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3353/health', timeout=3)"
CMD ["uvicorn", "http_app:app", "--host", "0.0.0.0", "--port", "3353"]
