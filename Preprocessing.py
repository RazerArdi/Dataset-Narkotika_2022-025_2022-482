import os
import re
import pandas as pd
from collections import defaultdict
import json

# --- [1] PERSIAPAN: Download Stopwords (hanya perlu sekali) ---
# Pastikan Anda sudah menjalankan ini sebelumnya di environment Anda.
# import nltk
# nltk.download('stopwords')
# nltk.download('punkt')

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# --- Konfigurasi ---
# Ganti nama file ini sesuai dengan file CSV hasil web scraping Anda
INPUT_CSV_FILE = 'putusan_pn_kendal_lengkap.csv' 
OUTPUT_CSV_FILE = 'putusan_lengkap_processed.csv'
OUTPUT_FOLDER = 'Preprocessing_Results'

# Menggunakan daftar stopword dari NLTK Bahasa Indonesia
try:
    list_stopwords = stopwords.words('indonesian')
except LookupError:
    print("Stopwords NLTK belum diunduh. Menjalankan nltk.download('stopwords')...")
    import nltk
    nltk.download('stopwords')
    list_stopwords = stopwords.words('indonesian')

# Menambahkan stopwords tambahan yang sering muncul di dokumen hukum
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

# --- [2] FUNGSI-FUNGSI PREPROCESSING ---

def case_folding(text):
    """Mengubah semua teks menjadi huruf kecil."""
    return text.lower()

def remove_special_characters(text):
    """Menghapus angka, tanda baca, dan karakter non-alfabet lainnya."""
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tokenizing(text):
    """Memecah teks menjadi token atau kata-kata individu."""
    try:
        return word_tokenize(text)
    except LookupError:
        print("Tokenizer 'punkt' NLTK belum diunduh. Menjalankan nltk.download('punkt')...")
        import nltk
        nltk.download('punkt')
        return word_tokenize(text)

def filtering_stopwords(tokens):
    """Menghapus kata-kata umum (stopwords) dari daftar token."""
    return [token for token in tokens if token not in list_stopwords and len(token) > 1]

# --- [3] FUNGSI-FUNGSI UTAMA ---

def preprocess_pipeline(text):
    """Menjalankan seluruh pipeline preprocessing pada sebuah teks."""
    if not isinstance(text, str) or pd.isna(text):
        return []
    text = case_folding(text)
    text = remove_special_characters(text)
    tokens = tokenizing(text)
    filtered_tokens = filtering_stopwords(tokens)
    return filtered_tokens

def build_inverted_index(df, token_column):
    """Membangun inverted index dari kolom yang sudah berisi token."""
    inverted_index = defaultdict(list)
    for doc_id, row in df.iterrows():
        tokens = row[token_column]
        for token in set(tokens):  # Hanya token unik per dokumen
            inverted_index[token].append(doc_id)
    return {k: sorted(v) for k, v in inverted_index.items()} # Mengurutkan hasil

# --- [4] EKSEKUSI ---
try:
    # Membuat folder output jika belum ada
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    print(f"📁 Folder '{OUTPUT_FOLDER}' siap digunakan.")

    # Membaca file CSV dari hasil scraping
    df = pd.read_csv(INPUT_CSV_FILE, index_col='No')
    print(f"✅ Berhasil memuat {len(df)} dokumen dari '{INPUT_CSV_FILE}'.")

    # Menggabungkan kolom relevan menjadi satu kolom teks untuk diproses
    print("Menggabungkan kolom 'Barang Bukti' dan 'Amar Putusan'...")
    df['Teks_Gabungan'] = df['Barang Bukti'].fillna('') + " " + df['Amar Putusan'].fillna('')

    # Melakukan preprocessing untuk setiap dokumen
    print("Memulai proses preprocessing untuk semua dokumen...")
    df['Processed_Tokens'] = df['Teks_Gabungan'].apply(preprocess_pipeline)

    # Menyimpan hasil preprocessing setiap dokumen ke file .txt terpisah
    print(f"Menyimpan hasil preprocessing ke folder '{OUTPUT_FOLDER}'...")
    for doc_id, row in df.iterrows():
        # Membuat nama file yang aman dari nomor putusan
        safe_filename = re.sub(r'[\/\\?%*:|"<>]', '_', str(row['NoPutusan'])) + '.txt'
        file_path = os.path.join(OUTPUT_FOLDER, safe_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(" ".join(row['Processed_Tokens']))
    print("✅ Semua hasil preprocessing telah disimpan sebagai file .txt.")

    # Menyimpan DataFrame yang sudah diperbarui (termasuk token) ke CSV baru
    df_to_save = df.drop(columns=['Teks_Gabungan']) # Hapus kolom gabungan sebelum menyimpan
    df_to_save.to_csv(OUTPUT_CSV_FILE)
    print(f"✅ Hasil gabungan disimpan dalam file '{OUTPUT_CSV_FILE}'.")

    # Membangun dan menampilkan Inverted Index
    print("-" * 50)
    print("Memulai proses indexing...")
    inverted_index = build_inverted_index(df, 'Processed_Tokens')
    print("✅ Proses indexing selesai.")
    print(f"Jumlah term unik dalam index: {len(inverted_index)}")

    # Menampilkan contoh hasil inverted index
    print("\nContoh isi Inverted Index (5 term pertama):")
    count = 0
    for term, doc_ids in sorted(inverted_index.items()):
        print(f"Term: '{term}' -> Dokumen (No): {doc_ids}")
        count += 1
        if count >= 5:
            break
            
    print("\nContoh pencarian term spesifik:")
    specific_terms = ['narkotika', 'shabu', 'hp', 'motor', 'ganja', 'pidana']
    for term in specific_terms:
        if term in inverted_index:
            print(f"Term: '{term}' -> Dokumen (No): {inverted_index[term]}")
        else:
            print(f"Term: '{term}' -> Tidak ditemukan.")
            
except FileNotFoundError:
    print(f"❌ ERROR: File '{INPUT_CSV_FILE}' tidak ditemukan.")
    print("Pastikan file tersebut berada di direktori yang sama dengan skrip ini.")
except Exception as e:
    print(f"❌ Terjadi kesalahan: {e}")