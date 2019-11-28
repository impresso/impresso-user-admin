FROM python:3.6.9-alpine

WORKDIR /impresso-user-admin

RUN pip install -U pipenv

COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv install --system --deploy --ignore-pipfile

RUN mkdir -p logs
COPY . .
