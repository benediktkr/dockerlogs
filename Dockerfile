FROM python:3.9 as base

ENV DEBIAN_FRONTEND noninteractive
ENV TZ Europe/Berlin
ENV TERM=xterm-256color

RUN pip install poetry
RUN apt-get update

ARG UID=1219
RUN useradd -m -u ${UID} sudois \
        && mkdir /sudois \
        && chown sudois:sudois /sudois \
        && poetry config virtualenvs.create false

WORKDIR /sudois

FROM base as dependencies
COPY --chown=sudois:sudois pyproject.toml /sudois
COPY --chown=sudois:sudois poetry.lock /sudois
RUN poetry install --no-interaction --no-root --ansi

# copying the app code and leaving it there for
# the final and builder stages, rather than making
# a new stage to do that
COPY --chown=sudois:sudois . /sudois/

FROM dependencies as builder
RUN poetry build --no-interaction --ansi

FROM dependencies as final
RUN poetry install --no-interaction --ansi

CMD ["dockertailer"]
