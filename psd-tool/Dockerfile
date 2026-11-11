FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install "psd-tools>=1.9,<2"

WORKDIR /app
COPY psd_fonts.py /app/psd_fonts.py

# Ohne Root-Rechte laufen; die PSD-Dateien werden read-only nach /data gemountet
RUN useradd --create-home --uid 1000 psd
USER psd
WORKDIR /data

ENTRYPOINT ["python3", "/app/psd_fonts.py"]
CMD ["--help"]
