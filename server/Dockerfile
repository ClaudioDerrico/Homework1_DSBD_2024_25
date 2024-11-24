FROM python:3.9-slim

WORKDIR /app

COPY server/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .


COPY common/ ./common

ENV PYTHONUNBUFFERED=1

CMD ["python", "server.py"]
