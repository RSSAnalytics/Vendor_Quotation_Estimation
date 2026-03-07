FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libfreetype6-dev \
    libpng-dev \
    zlib1g-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD gunicorn app:app --bind 0.0.0.0:$PORT
```

---

Also update your `requirements.txt` back to the latest xhtml2pdf (no version pin needed now):
```
Flask
mysql-connector-python
gunicorn
APScheduler
xhtml2pdf
Pillow
