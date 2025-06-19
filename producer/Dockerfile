FROM python:3.10.13-slim-bookworm

WORKDIR /producer

COPY . .
RUN pip install -U pip && \
    pip install -r requirements.txt

WORKDIR /producer/src
ENTRYPOINT ["python3", "-m", "main"]