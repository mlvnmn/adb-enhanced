# Build Stage for Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Final Stage
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend and install dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
RUN pip install --no-cache-dir gunicorn eventlet

# Copy built frontend to backend/static (so Flask can serve it)
COPY --from:frontend-builder /app/frontend/dist ./backend/static

# Copy all source code
COPY . .

# Environment variables for Demo Mode
ENV RENDER=true
ENV PORT=7860

# Expose the port Hugging Face uses
EXPOSE 7860

# Start script
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:7860", "--chdir", "backend", "app:app"]
