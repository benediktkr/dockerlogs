FROM python:3.9 as base

ENV DEBIAN_FRONTEND noninteractive
ENV TZ Europe/Berlin
ENV TERM=xterm-256color

RUN pip install poetry

ARG UID=1219
RUN useradd -m -u ${UID} sudois \
        && mkdir /sudois \
        && chown sudois:sudois /sudois \
        && poetry config virtualenvs.create false #?

WORKDIR /sudois

FROM base as builder

COPY --chown=sudois:sudois pyproject.toml /sudois
COPY --chown=sudois:sudois poetry.lock /sudois
COPY --chown=sudois:sudois . /sudois
RUN poetry build --no-interaction --ansi

FROM base as final

COPY --chown=sudois:sudois dockerlogs/ /sudois/dockerlogs
RUN poetry install --no-interaction --no-root --ansi

USER root
CMD ["dockerlogs"]
