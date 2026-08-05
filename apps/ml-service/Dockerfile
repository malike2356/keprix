FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .
COPY . /app/

EXPOSE 8200
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200"]
