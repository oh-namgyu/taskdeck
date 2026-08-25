FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    TASKDECK_HOST=0.0.0.0 \
    TASKDECK_PORT=6090 \
    TASKDECK_DATA=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY taskdeck ./taskdeck
COPY run.py .

# Run as a non-root user; /data is a writable volume mount.
RUN useradd --create-home --uid 10001 taskdeck \
    && mkdir -p /data && chown -R taskdeck:taskdeck /data /app
USER taskdeck

EXPOSE 6090
CMD ["python", "run.py"]
