FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# wkhtmltopdf (patched qt) ставим из официального пакета wkhtmltox —
# в репозиториях Debian его больше нет. Бинарь оказывается в /usr/local/bin.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget ca-certificates fontconfig libjpeg62-turbo libxext6 libxrender1 xfonts-75dpi xfonts-base \
    && wget -q "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_$(dpkg --print-architecture).deb" -O /tmp/wkhtmltox.deb \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -f /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "wsgi:app"]
