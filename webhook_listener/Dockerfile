FROM python:3.9-slim as base
WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y curl && apt-get clean
ENV POETRY_VERSION=1.4.2
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python -

ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.in-project true

# Setup project
RUN mkdir listener && touch listener/__init__.py
COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --no-dev

FROM python:3.9-slim as final
WORKDIR /usr/src/app
COPY --from=base /usr/src/app/.venv /usr/src/app/.venv
ENV PATH="/usr/src/app/.venv/bin:$PATH"

COPY listener/ listener/

ENTRYPOINT ["python", "-m", "listener"]
