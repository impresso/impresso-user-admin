FROM python:3.6.9-alpine

WORKDIR /impresso-user-admin

ARG GIT_TAG
ARG GIT_BRANCH
ARG GIT_REVISION

RUN pip install -U pipenv

COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile

RUN mkdir -p logs
COPY . .

ENV IMPRESSO_GIT_TAG=${GIT_TAG}
ENV IMPRESSO_GIT_BRANCH=${GIT_BRANCH}
ENV IMPRESSO_GIT_REVISION=${GIT_REVISION}
