# %%
from datetime import datetime
import json
import random
import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


options = uc.ChromeOptions()
# options.add_argument("--headless=new") sementara ini bisa digunakan jika ingin menjalankan browser tanpa GUI
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# Opsional: jalankan tanpa GUI/headless jika dibutuhkan
# options.add_argument("--headless")

driver = uc.Chrome(
    version_main=151,  # Sesuaikan dengan versi Chrome di komputermu jika perlu
    options=options
)


TARGET_COLUMNS = [
    "scraped_at",
    "link",
    "item_sku",
    "product_sku",
    "product_code",
    "nama_produk",
    "merk",
    "harga_asli",
    "harga_setelah_diskon",
    "nominal_diskon",
    "stok",
    "seller",
    "rating_produk",
    "jumlah_ulasan_produk",
    "rating_seller",
    "deskripsi_singkat",
]

def clean_html_text(value):
    if value is None:
        return None
    text = BeautifulSoup(str(value).replace("<br>", "\n"), "html.parser").get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text).strip()
    return text or None

def extract_initial_state(page_source):
    marker = "window.__PRODUCT_DETAIL_INITIAL_STATE__ = "
    start = page_source.find(marker)
    if start == -1:
        return {}
    start += len(marker)
    end = page_source.find("};window.PRODUCT_DETAIL_SERVER_CACHE", start)
    if end == -1:
        end = page_source.find("</script>", start)
        raw = page_source[start:end].strip().rstrip(";")
    else:
        raw = page_source[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

def get_summary_from_state(state):
    return state.get("productDetail.product/summary") or {}


def scrape_product_detail(driver, url, scroll=True):
    scraped_at = datetime.now().isoformat()
    driver.get(url)
    time.sleep(random.uniform(3, 5))

    # Mengambil URL akhir setelah redirect (penting untuk link shortener Blibli)
    final_url = driver.current_url

    if scroll:
        for i in range(5):
            driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight/5*{i+1});")
            time.sleep(0.8)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    summary = get_summary_from_state(extract_initial_state(html))

    price = summary.get("price") or {}
    brand = summary.get("brand") or {}
    merchant = summary.get("merchant") or {}
    merchant_rating = merchant.get("rating") or {}
    review = summary.get("review") or {}

    data = {
        "scraped_at": scraped_at,
        "link": final_url,  # Menggunakan URL final
        "item_sku": summary.get("itemSku"),
        "product_sku": summary.get("productSku"),
        "product_code": summary.get("productCode"),
        "nama_produk": summary.get("name"),
        "merk": brand.get("name"),
        "harga_asli": price.get("listed"),
        "harga_setelah_diskon": price.get("offered"),
        "nominal_diskon": price.get("totalDiscount"),
        "stok": summary.get("stock"),
        "seller": merchant.get("name"),
        "rating_produk": review.get("decimalRating"),
        "jumlah_ulasan_produk": review.get("count"),
        "rating_seller": merchant_rating.get("review"),
        "deskripsi_singkat": clean_html_text(summary.get("uniqueSellingPoint")),
    }

    # Fallback jika data tidak ada di window initial state
    if not data["nama_produk"]:
        tag = soup.select_one(".product-info__product-name")
        data["nama_produk"] = tag.get_text(strip=True) if tag else None
    if not data["seller"]:
        tag = soup.select_one(".seller-name__name")
        data["seller"] = tag.get_text(strip=True) if tag else None
    if not data["merk"]:
        tag = soup.select_one('[data-testid="descriptionInfoBrand"]')
        data["merk"] = tag.get_text(strip=True) if tag else None
    if not data["deskripsi_singkat"]:
        tag = soup.select_one('[data-testid="descriptionInfo"]')
        data["deskripsi_singkat"] = tag.get_text("\n", strip=True) if tag else None

    return data


def save_to_supabase(data):
    """
    Mengirimkan dict hasil scraping ke tabel product_scrapes di Supabase
    """
    if not data:
        print("Data kosong, tidak disave.")
        return

    # Filter hanya kolom yang sesuai dengan TARGET_COLUMNS
    payload = {k: data.get(k) for k in TARGET_COLUMNS if k in data}

    try:
        response = supabase.table("product_scrapes").upsert(payload).execute()
        print(f"Berhasil tersimpan di Supabase: {payload.get('nama_produk')}")
    except Exception as e:
        print(f"Gagal menyimpan ke Supabase: {str(e)}")


url_produk = [
    "https://blibli.onelink.me/GNtk/r6jfhfgi",
    "https://blibli.onelink.me/GNtk/93bnf6o0",
    "https://blibli.onelink.me/GNtk/dvlyu89j",
    "https://blibli.onelink.me/GNtk/5zmam5vf",
    "https://blibli.onelink.me/GNtk/eb77elrb",
    "https://blibli.onelink.me/GNtk/jjhb65bn"
]

hasil = []

for url in url_produk:
    if not isinstance(url, str):
        print(f"Skipping invalid URL entry: {url!r}")
        continue

    print(f"Scraping URL: {url} ...")
    product = scrape_product_detail(driver, url)
    
    # Simpan ke Supabase per produk
    save_to_supabase(product)
    
    # Masukkan ke list untuk DataFrame
    hasil.append(product)

# Tutup driver browser setelah selesai
driver.quit()

# Convert list of dicts ke Pandas DataFrame secara benar
df = pd.DataFrame(hasil)

print("\n--- Hasil Scraping ---")
print(df)
# %%
