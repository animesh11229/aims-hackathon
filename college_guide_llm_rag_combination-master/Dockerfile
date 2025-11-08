FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Gunicorn or Waitress both work; pick one
# EXAMPLE (gunicorn + wsgi.py with `app`):
EXPOSE 80
CMD ["gunicorn", "-b", "0.0.0.0:80", "wsgi:app"]
