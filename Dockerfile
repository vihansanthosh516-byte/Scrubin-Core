# ScrubIn-Core — Python simulation engine (FastAPI), served on port 8001.
#
# Only the light core requirements are installed. The heavy scientific stack
# (torch, numpy, gymnasium, ...) lives in requirements-optional.txt and is
# lazy-imported behind try/except, so it is NOT pulled into the image.
#
# Build (from docker-compose at the scrubin root, context = this repo):
#   docker compose build engine

FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Production: bind all interfaces, fixed port, no reloader (the reloader would
# spawn a second worker and leave orphans when the container restarts).
ENV SCRUBIN_CORE_HOST=0.0.0.0 \
    SCRUBIN_CORE_PORT=8001 \
    SCRUBIN_CORE_RELOAD=0

EXPOSE 8001
CMD ["python", "server.py"]
