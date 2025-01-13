FROM python:3.11-slim

WORKDIR /opt/app

COPY . .

RUN pip install --no-cache-dir .

ENTRYPOINT [ "python", "app.py" ]