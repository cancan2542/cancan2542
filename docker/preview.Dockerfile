# Headless Chromium for rendering preview screenshots of dist/*.svg
FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app
USER app

WORKDIR /app
ENTRYPOINT ["sh", "scripts/preview.sh"]
