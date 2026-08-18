# 1. Gunakan sistem operasi Linux dengan Python 3.12 bawaan
FROM python:3.12-slim

# 2. Install dependencies sistem yang dibutuhkan untuk mendownload Chrome
RUN apt-get update && apt-get install -y wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Download dan Install Google Chrome versi stabil terbaru
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# 4. Buat dan atur folder kerja di dalam container dengan nama /app
WORKDIR /app

# 5. Copy file requirements.txt dari laptopmu ke dalam container
COPY requirements.txt .

# 6. Install semua library Python yang ada di requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy seluruh sisa file project (termasuk scrape_blibli.py) ke dalam container
COPY . .

# 8. Perintah yang akan dieksekusi otomatis oleh Render saat jalan
CMD ["python", "scrape_blibli.py"]