FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./ai_self_healing_backend /app/ai_self_healing_backend

ENV PORT=9000

EXPOSE 9000

CMD ["uvicorn", "ai_self_healing_backend.app.main:app", "--host=0.0.0.0", "--port=9000"]

