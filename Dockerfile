FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV MODEL_DEVICE=cpu
ENV MINDFUL_CHECKPOINT_DIR=/app/checkpoints

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY model /app/model
COPY scripts /app/scripts
COPY checkpoints/embed_matrix.npy /app/checkpoints/embed_matrix.npy
COPY checkpoints/vocab.pkl /app/checkpoints/vocab.pkl

CMD ["python", "scripts/start_backend.py"]
