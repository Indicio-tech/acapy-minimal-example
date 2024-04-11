FROM python:3.10
WORKDIR /usr/src/app/

ENV POETRY_VERSION=1.5.1
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python -

ENV PATH="/opt/poetry/bin:$PATH"
RUN poetry config virtualenvs.in-project true

# Setup project
RUN mkdir acapy_controller && touch acapy_controller/__init__.py
COPY pyproject.toml poetry.lock ./
ARG install_flags=--no-dev
RUN poetry install ${install_flags} -E models

COPY acapy_controller/ acapy_controller/

ENTRYPOINT ["poetry", "run"]
