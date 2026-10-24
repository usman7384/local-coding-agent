# Sandbox for agent tool execution and grading. Built once; one fresh container per attempt.
FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4 \
    && useradd --create-home --uid 1000 agent \
    && mkdir /work && chown agent:agent /work

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=0

USER agent
WORKDIR /work
CMD ["sleep", "infinity"]
