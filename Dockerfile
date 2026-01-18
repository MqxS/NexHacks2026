FROM node:20-bullseye

# Install Python and system dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# Install Python deps
RUN if [ -f requirements.txt ]; then \
      python3 -m pip install --no-cache-dir -r requirements.txt; \
    else \
      python3 -m pip install --no-cache-dir flask requests gunicorn; \
    fi

# Build frontend if it exists
RUN if [ -d frontend ]; then \
      cd frontend && \
      npm ci --silent || npm install --silent && \
      npm run build; \
    fi

EXPOSE 8080

# Just run the backend
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:server"]
