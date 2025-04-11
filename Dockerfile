FROM python:3.11-slim

# Cài thư viện hệ thống cần thiết cho Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates curl unzip fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libxshmfence1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Cài pip packages
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cài Chromium bằng Playwright
RUN pip install playwright
RUN playwright install chromium

# Copy toàn bộ mã nguồn
COPY . .

CMD ["python", "app-web-qnpc-fn.py"]