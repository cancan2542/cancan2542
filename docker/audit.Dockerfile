# pip-audit for the generator image's installed packages (see .claude/hooks/security-gate.sh)
#   (the hook lists profile-generator's packages via importlib.metadata into req.txt)
#   docker compose run --rm -T -v "$PWD:/scan:ro" audit -r /scan/req.txt --no-deps --disable-pip
FROM python:3.13-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install pip-audit==2.10.1

RUN useradd --create-home --uid 1000 app
USER app

ENTRYPOINT ["pip-audit", "--strict", "--desc", "on"]
