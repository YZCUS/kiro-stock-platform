FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN addgroup --system --gid 1001 qlib \
    && adduser --system --uid 1001 --ingroup qlib qlib \
    && mkdir -p /app/artifacts \
    && chown -R qlib:qlib /app

USER qlib

EXPOSE 8090

ENV OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    NUMEXPR_NUM_THREADS=2

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers ${QLIB_WORKERS:-2}"]
