FROM python:3.9-slim

WORKDIR /app

COPY data_collector/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY data_collector/ .

COPY common/ ./common

ENV PYTHONUNBUFFERED=1

CMD ["python", "collector.py"]
