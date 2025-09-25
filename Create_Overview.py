import os
import re
import glob
import pandas as pd
import pdfplumber

# --- PENGATURAN ---
DATA_FOLDER = "Data"
OUTPUT_FOLDER = "Overview"
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "Overview.xlsx")

def extract_text_from_pdf(pdf_path):
    """Mengekstrak seluruh teks dari file PDF."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            return full_text
    except Exception as e:
        print(f"  -> Gagal membaca PDF {os.path.basename(pdf_path)}: {e}")
        return ""

def clean_text(text):
    """Membersihkan spasi dan baris baru yang berlebih."""
    return re.sub(r'\s+', ' ', text).strip()

def extract_information(full_text):
    """Mengekstrak informasi spesifik dari teks putusan menggunakan regex."""
    info = {
        "No Putusan": "Tidak Ditemukan",
        "Lembaga Peradilan": "Pengadilan Negeri Kendal",
        "Barang Bukti": "Tidak Ditemukan",
        "Amar Putusan": "Tidak Ditemukan"
    }

    # 1. Ekstrak Nomor Putusan
    match_no = re.search(r"PUTUSAN\s*Nomor\s*([\w.\/]+)", full_text, re.IGNORECASE)
    if match_no:
        info["No Putusan"] = clean_text(match_no.group(1))

    # 2. Ekstrak Amar Putusan (bagian MENGADILI)
    # Mencari dari kata "MENGADILI" sampai akhir dokumen atau sampai bagian hakim
    match_amar = re.search(r"M\s*E\s*N\s*G\s*A\s*D\s*I\s*L\s*I\s*:?\s*(.*?)(Demikianlah diputuskan|Hakim Ketua|Panitera Pengganti)", full_text, re.DOTALL | re.IGNORECASE)
    if match_amar:
        info["Amar Putusan"] = clean_text(match_amar.group(1))

    # 3. Ekstrak Barang Bukti
    # Mencari dari frasa "Menetapkan barang bukti berupa" sampai akhir amar atau frasa penutup
    match_bb = re.search(r"Menetapkan barang bukti berupa\s*:\s*(.*?)(Membebankan kepada|Demikianlah diputuskan)", full_text, re.DOTALL | re.IGNORECASE)
    if match_bb:
        info["Barang Bukti"] = clean_text(match_bb.group(1))
    
    return info

def main():
    """Fungsi utama untuk memproses semua PDF dan membuat file Excel."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # Mencari semua file .pdf di dalam folder Data dan subfoldernya
    pdf_files = glob.glob(os.path.join(DATA_FOLDER, '**', '*.pdf'), recursive=True)
    
    if not pdf_files:
        print(f"❌ Tidak ada file PDF yang ditemukan di dalam folder '{DATA_FOLDER}'.")
        print("Pastikan Anda sudah menjalankan 'Scrapping.py' terlebih dahulu.")
        return

    print(f"✅ Ditemukan {len(pdf_files)} file PDF untuk diproses.")
    
    all_data = []
    for pdf_path in pdf_files:
        print(f"\nMemproses: {os.path.basename(pdf_path)}...")
        
        # Ekstrak teks mentah dari PDF
        text = extract_text_from_pdf(pdf_path)
        
        if text:
            # Ekstrak informasi terstruktur
            data = extract_information(text)
            all_data.append(data)
            print("  -> Ekstraksi berhasil.")
        else:
            print("  -> Ekstraksi gagal, file dilewati.")

    if not all_data:
        print("Tidak ada data yang berhasil diekstrak dari file PDF.")
        return

    # Membuat DataFrame dan menyimpannya ke Excel
    df = pd.DataFrame(all_data)
    df.index.name = 'No'
    df.index = df.index + 1
    
    # Mengatur urutan kolom
    df = df[["No Putusan", "Lembaga Peradilan", "Barang Bukti", "Amar Putusan"]]
    
    df.to_excel(OUTPUT_FILE)
    
    print(f"\n🚀 PROSES SELESAI! File '{OUTPUT_FILE}' berhasil dibuat dengan {len(df)} data.")

if __name__ == "__main__":
    main()