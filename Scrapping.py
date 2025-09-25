import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin
import re

# --- PENGATURAN ---
TARGET_DOKUMEN = 50  # Jumlah minimum dokumen yang akan di-scrape
TAHUN_MULAI = 2025     # Mulai scraping dari tahun ini

BASE_URL = "https://putusan3.mahkamahagung.go.id/direktori/index/pengadilan/pn-kendal/kategori/narkotika-dan-psikotropika-1"
DOWNLOAD_BASE_URL = "https://putusan3.mahkamahagung.go.id"
DATA_FOLDER = "Data"

# Pengaturan untuk mekanisme retry
JUMLAH_PERCOBAAN = 10
JEDA_PERCOBAAN = 5
TIMEOUT_REQUEST = 110

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    """Mengambil konten dari URL dengan mekanisme retry."""
    for percobaan in range(JUMLAH_PERCOBAAN):
        try:
            print(f"Mencoba mengambil URL: {url} (Percobaan {percobaan + 1}/{JUMLAH_PERCOBAAN})")
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_REQUEST)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"  -> Gagal: {e}. Menunggu {JEDA_PERCOBAAN} detik...")
            time.sleep(JEDA_PERCOBAAN)
    print(f"Gagal total mengambil URL {url} setelah {JUMLAH_PERCOBAAN} kali percobaan.")
    return None

def download_pdf(pdf_url, save_folder, fallback_filename):
    """
    Mengunduh PDF dan menyimpannya dengan nama file asli dari server.
    """
    for percobaan in range(JUMLAH_PERCOBAAN):
        try:
            print(f"  -> Memulai unduhan dari {pdf_url}...")
            pdf_response = requests.get(pdf_url, headers=HEADERS, stream=True, timeout=TIMEOUT_REQUEST)
            pdf_response.raise_for_status()

            # --- LOGIKA BARU UNTUK NAMA FILE ---
            filename = fallback_filename
            content_disp = pdf_response.headers.get('content-disposition')
            if content_disp:
                # Mencari 'filename=' di dalam header
                fname_match = re.search('filename="(.+?)"', content_disp)
                if fname_match:
                    filename = fname_match.group(1)

            file_path = os.path.join(save_folder, filename)

            if os.path.exists(file_path):
                print(f"  -> File sudah ada: {filename}. Dilewati.")
                return True

            with open(file_path, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  ✅ Berhasil mengunduh: {filename}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"  -> Gagal mengunduh (percobaan {percobaan + 1}): {e}. Menunggu {JEDA_PERCOBAAN} detik...")
            time.sleep(JEDA_PERCOBAAN)

    print(f"  ❌ Gagal total mengunduh PDF dari {pdf_url}.")
    return False

def main():
    """Fungsi utama untuk menjalankan proses scraping."""
    all_data = []
    current_year = TAHUN_MULAI

    # --- LOGIKA BARU: LOOP HINGGA TARGET DOKUMEN TERCAPAI ---
    while len(all_data) < TARGET_DOKUMEN:
        print(f"\n{'='*25} MEMULAI SCRAPING TAHUN {current_year} {'='*25}")
        
        year_folder = os.path.join(DATA_FOLDER, str(current_year))
        os.makedirs(year_folder, exist_ok=True)

        current_page_url = f"{BASE_URL}/tahun/{current_year}.html"
        is_year_done = False

        while current_page_url and not is_year_done:
            soup = get_soup(current_page_url)
            if not soup:
                break

            decision_items = soup.select('div.spost.clearfix')
            if not decision_items:
                print(f"Tidak ada putusan ditemukan di halaman: {current_page_url}")
                break

            print(f"Menemukan {len(decision_items)} putusan di halaman ini.")

            for item in decision_items:
                if len(all_data) >= TARGET_DOKUMEN:
                    is_year_done = True
                    break # Hentikan jika target sudah tercapai di tengah halaman

                link_tag = item.select_one('strong > a')
                if not link_tag or not link_tag.has_attr('href'): continue

                detail_url = link_tag['href']
                print(f"\nMemproses: {link_tag.text.strip()} ({len(all_data) + 1}/{TARGET_DOKUMEN})")
                
                detail_soup = get_soup(detail_url)
                if not detail_soup: continue

                nomor_putusan = detail_soup.select_one('h1').get_text(separator="<br>").split('<br>')[-1].strip()
                lembaga_peradilan_elem = detail_soup.find("td", string="Lembaga Peradilan")
                lembaga_peradilan = lembaga_peradilan_elem.find_next_sibling("td").text.strip() if lembaga_peradilan_elem else "PN KENDAL"

                pdf_link_tag = detail_soup.find('a', href=lambda href: href and '/download_file/' in href and '/pdf/' in href)
                
                if pdf_link_tag:
                    pdf_url = urljoin(DOWNLOAD_BASE_URL, pdf_link_tag['href'])
                    fallback_filename = nomor_putusan.replace('/', '_').replace('.', '') + ".pdf"
                    download_pdf(pdf_url, year_folder, fallback_filename)
                else:
                    print(f"  ⚠️ Tidak ditemukan link PDF untuk putusan {nomor_putusan}")

                all_data.append({
                    "NoPutusan": nomor_putusan, "LembagaPeradilan": lembaga_peradilan,
                    "BarangBukti": "", "AmarPutusan": "", "Link": detail_url
                })
                time.sleep(1)

            # Pagination
            next_page_tag = soup.select_one('a.page-link[rel="next"]')
            if next_page_tag and next_page_tag.has_attr('href') and not is_year_done:
                current_page_url = next_page_tag['href']
                print(f"\n---> Lanjut ke halaman berikutnya: {current_page_url}")
            else:
                current_page_url = None

        current_year -= 1 # Pindah ke tahun sebelumnya
        if current_year < 2010: # Batas aman agar tidak loop selamanya
             print("Mencapai tahun batas, menghentikan pencarian.")
             break

    if all_data:
        df = pd.DataFrame(all_data)
        df.index += 1
        df.index.name = "No"
        df = df[["NoPutusan", "LembagaPeradilan", "BarangBukti", "AmarPutusan", "Link"]]
        csv_path = "putusan_pn_kendal_lengkap.csv"
        df.to_csv(csv_path)
        print(f"\n🚀 PROSES SELESAI. Total {len(df)} data berhasil dikumpulkan dan disimpan di {csv_path}")
    else:
        print("\nTidak ada data yang berhasil di-scrape.")

if __name__ == "__main__":
    main()