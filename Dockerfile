FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
# pip is not needed at runtime; removing it also drops its vendored libs (urllib3, msgpack, ...) from scans
RUN pip install -r requirements.txt \
 && pip uninstall -y pip

RUN useradd --create-home --uid 1000 app
USER app

ENTRYPOINT ["python", "scripts/generate.py"]
