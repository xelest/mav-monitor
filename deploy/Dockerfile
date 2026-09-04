FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONITOR_HOST=0.0.0.0 \
    MONITOR_PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mav_monitor ./mav_monitor

EXPOSE 8080
USER nobody

ENTRYPOINT ["python", "-m", "mav_monitor"]
