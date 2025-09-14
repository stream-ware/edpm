FROM python:3.9-alpine

RUN apk add --no-cache zeromq-dev gcc musl-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "edpm-lite-server.py"]
