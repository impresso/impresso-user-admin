FROM python:3.12.2-alpine

RUN set -ex \
  # Create a non-root user
  && addgroup --system --gid 1001 appgroup \
  && adduser --system --uid 1001  --no-create-home appuser -G appgroup \
  # Upgrade the package index and install security upgrades
  && apk update \
  && apk upgrade \
  && apk --no-cache add ca-certificates \
  && rm -rf /var/cache/apk/*

WORKDIR /impresso-user-admin
RUN chown -R appuser:appgroup /impresso-user-admin
RUN mkdir -p /impresso-user-admin/logs
RUN touch /impresso-user-admin/logs/debug.log
RUN chown appuser:appgroup /impresso-user-admin/logs/debug.log
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
# Set the user to run the application
USER appuser