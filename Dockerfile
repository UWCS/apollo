FROM python:3.10 AS builder


RUN pip install --user pipenv

# Tell pipenv to create venv in the current directory
ENV PIPENV_VENV_IN_PROJECT=1

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY Pipfile /app/Pipfile
COPY Pipfile.lock /app/Pipfile.lock

WORKDIR /app

RUN /root/.local/bin/pipenv sync

COPY .git .git
RUN echo $(git rev-parse --short HEAD) > .version
RUN echo $(date -Is) >> .version

FROM python:3.10-slim AS runtime


WORKDIR /app

# copy venv into runtime
COPY --from=builder /app/.venv/ /app/.venv/
COPY --from=builder /app/.version /app/.version


# add venv to path
ENV PATH="/app/.venv/bin:$PATH"

# let apollo know that it's in a container
ENV CONTAINER=1

# copy in everything
COPY . /app

# build default alembic config into container, we rarely want to change this
RUN /bin/bash -c 'if [[ ! -f alembic.ini ]]; then mv alembic.example.ini alembic.ini; fi'

RUN apt-get update
RUN apt-get install -y python3-cairo

CMD [ "python", "apollo.py" ] 
