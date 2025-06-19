FROM python:3.10.13-slim-bookworm

WORKDIR /frontend

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

WORKDIR /frontend/src

ENTRYPOINT ["python3", "-m", "streamlit", "run", "main.py"]
