import os
import re
import pandas as pd
from collections import defaultdict
import fitz  # Library untuk membaca PDF (PyMuPDF)
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# GANTI FUNGSI LAMA DENGAN YANG BARU INI

# --- [1] FUNGSI UNTUK PERSIAPAN NLTK ---
def setup_nltk():
    """Mengunduh paket NLTK yang diperlukan jika belum ada."""
    import nltk  # <-- TAMBAHKAN IMPORT INI DI SINI
    try:
        stopwords.words('indonesian')
    except LookupError:
        print("Mengunduh NLTK 'stopwords'...")
        nltk.download('stopwords')
    try:
        word_tokenize("test")
    except LookupError:
        print("Mengunduh NLTK 'punkt' dan paket tambahannya...")
        nltk.download('punkt')
        nltk.download('punkt_tab') # <-- TAMBAHKAN BARIS INI

# --- [2] KONFIGURASI ---
DATA_ROOT_FOLDER = 'Data'  # Folder utama berisi subfolder 2023, 2024, dst.
OUTPUT_CSV_FILE = 'putusan_pdf_processed.csv'
OUTPUT_FOLDER = 'Preprocessing_Results_PDF'

# Menjalankan persiapan NLTK
setup_nltk()

# Mempersiapkan daftar stopwords
list_stopwords = stopwords.words('indonesian')
custom_stopwords = [
    'terdakwa', 'bahwa', 'saksi', 'rupiah', 'telah', 'dalam', 'dan', 'yang',
    'bin', 'binti', 'dengan', 'pada', 'dari', 'oleh', 'di', 'ke', 'itu', 'ini',
    'tersebut', 'adalah', 'yaitu', 'sebagai', 'atas', 'nomor', 'alias',
    'menetapkan', 'menyatakan', 'menjatuhkan', 'membebankan', 'pidana',
    'penjara', 'denda', 'bulan', 'tahun', 'gram', 'satu', 'dua', 'tiga', 'empat',
    'lima', 'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh', 'ribu', 'juta', 'milyar',
    'pasal', 'ayat', 'uu', 'ri', 'nomor', 'tentang', 'jo', 'dkk', 'sh', 'mh', 'alm',
    'untuk', 'para', 'sdr', 'hari', 'tanggal', 'wib', 'saat', 'melakukan',
    'perbuatan', 'tindak', 'hukum', 'putusan', 'negeri', 'pengadilan', 'rp', 'bahwa',
    'akta', 'alat', 'bukti', 'benar', 'berikut', 'didakwa', 'gugatan', 'hal', 'hakim',
    'tergugat', 'penggugat', 'pemohon', 'termohon', 'majelis', 'mengadili'
]
list_stopwords.extend(custom_stopwords)
list_stopwords = set(list_stopwords)

# --- [3] FUNGSI-FUNGSI PREPROCESSING (Tidak ada perubahan) ---
def case_folding(text):
    return text.lower()

def remove_special_characters(text):
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tokenizing(text):
    return word_tokenize(text)

def filtering_stopwords(tokens):
    return [token for token in tokens if token not in list_stopwords and len(token) > 1]

def preprocess_pipeline(text):
    if not isinstance(text, str) or pd.isna(text):
        return []
    text = case_folding(text)
    text = remove_special_characters(text)
    tokens = tokenizing(text)
    filtered_tokens = filtering_stopwords(tokens)
    return filtered_tokens

# --- [4] FUNGSI UTAMA (Tidak ada perubahan) ---
def build_inverted_index(df, token_column):
    inverted_index = defaultdict(list)
    for doc_id, row in df.iterrows():
        tokens = row[token_column]
        for token in set(tokens):
            inverted_index[token].append(doc_id)
    return {k: sorted(v) for k, v in inverted_index.items()}

# --- [5] EKSEKUSI UTAMA (Logika diubah total) ---
def main():
    """Fungsi utama untuk menjalankan seluruh proses."""
    try:
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        print(f"📁 Folder '{OUTPUT_FOLDER}' siap digunakan.")

        # --- MEMBACA SEMUA FILE PDF DARI FOLDER ---
        print(f"Mencari dan membaca file PDF dari folder '{DATA_ROOT_FOLDER}'...")
        dokumen_list = []
        if not os.path.isdir(DATA_ROOT_FOLDER):
            raise FileNotFoundError(f"Folder '{DATA_ROOT_FOLDER}' tidak ditemukan.")

        for root, _, files in os.walk(DATA_ROOT_FOLDER):
            for file in files:
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    try:
                        doc = fitz.open(file_path)
                        isi_teks_lengkap = "".join(page.get_text() for page in doc)
                        dokumen_list.append({
                            'NoPutusan': file,
                            'Path': file_path,
                            'Teks_Gabungan': isi_teks_lengkap
                        })
                    except Exception as e:
                        print(f"  Gagal membaca {file_path}: {e}")
        
        if not dokumen_list:
            print(f"❌ Tidak ada file PDF yang ditemukan di dalam folder '{DATA_ROOT_FOLDER}'.")
            return

        df = pd.DataFrame(dokumen_list)
        df.set_index('NoPutusan', inplace=True, drop=False)
        print(f"\n✅ Berhasil memuat dan memproses {len(df)} dokumen PDF.")

        # --- MELAKUKAN PREPROCESSING ---
        print("\nMemulai proses preprocessing untuk semua dokumen...")
        df['Processed_Tokens'] = df['Teks_Gabungan'].apply(preprocess_pipeline)

        # --- MENYIMPAN HASIL ---
        print(f"Menyimpan hasil preprocessing ke folder '{OUTPUT_FOLDER}'...")
        for doc_id, row in df.iterrows():
            safe_filename = re.sub(r'[\/\\?%*:|"<>]', '_', str(doc_id)) + '.txt'
            file_path = os.path.join(OUTPUT_FOLDER, safe_filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(" ".join(row['Processed_Tokens']))
        print("✅ Semua hasil preprocessing telah disimpan sebagai file .txt.")

        df_to_save = df.drop(columns=['Teks_Gabungan', 'Path', 'NoPutusan'])
        df_to_save.to_csv(OUTPUT_CSV_FILE)
        print(f"✅ Hasil gabungan disimpan dalam file '{OUTPUT_CSV_FILE}'.")

        # --- MEMBANGUN INVERTED INDEX ---
        print("-" * 50)
        print("Memulai proses indexing...")
        inverted_index = build_inverted_index(df, 'Processed_Tokens')
        print("✅ Proses indexing selesai.")
        print(f"Jumlah term unik dalam index: {len(inverted_index)}")

        # --- MENAMPILKAN CONTOH HASIL ---
        print("\nContoh isi Inverted Index (5 term pertama):")
        count = 0
        for term, doc_ids in sorted(inverted_index.items()):
            print(f"Term: '{term}' -> Dokumen: {doc_ids}")
            count += 1
            if count >= 5:
                break
        
        print("\nContoh pencarian term spesifik:")
        specific_terms = ['narkotika', 'shabu', 'hp', 'motor', 'ganja', 'pidana']
        for term in specific_terms:
            if term in inverted_index:
                print(f"Term: '{term}' -> Ditemukan di {len(inverted_index[term])} dokumen.")
            else:
                print(f"Term: '{term}' -> Tidak ditemukan.")

    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")

# Menjalankan skrip
if __name__ == "__main__":
    main()