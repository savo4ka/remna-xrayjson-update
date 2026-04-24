FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py remnawave_client.py ./
COPY templates ./templates

CMD ["python", "-u", "main.py"]
