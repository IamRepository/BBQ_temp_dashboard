# Probe-2-Plot for a home server (Synology Container Manager or any Docker host).
# Same setup as the Bresaola Tracker on the NAS. The project library lives in /data (a folder on the NAS).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    P2P_MODE=library \
    P2P_DATA=/data \
    TZ=Europe/Berlin

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .

VOLUME /data
EXPOSE 8522
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8522/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.port=8522", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
