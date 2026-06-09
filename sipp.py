import streamlit as st
import pandas as pd
import io
import re

# Konfigurasi halaman
st.set_page_config(
    page_title="Cleansing Data Perkara Perusahaan",
    page_icon="📊",
    layout="wide"
)

# Judul
st.title("📊 Aplikasi Cleansing Data Perkara Perusahaan")
st.markdown("""
Upload multiple file Excel, sistem akan:
1. **Memfilter** hanya baris dengan klasifikasi yang relevan terhadap masalah keuangan perusahaan
2. **Memisahkan kolom Para Pihak** menjadi Penggugat/Penuntut Umum dan Tergugat/Terdakwa
""")

# Klasifikasi yang direkomendasikan
RELEVANT_CLASSIFICATIONS = [
    "Ganti Rugi",
    "Perbuatan Melawan Hukum",
    "Penipuan",
    "Penggelapan",
    "Perbuatan Merugikan Pemiutang atau Orang Yang Mempunyai Hak",
    "Perselisihan Pemutusan Hubungan Kerja Massal",
    "Perselisihan Pemutusan Hubungan Kerja Sepihak"
]

# Kolom yang dipertahankan (dengan 2 kolom baru hasil pemisahan)
OUTPUT_COLUMNS = [
    "CIF", 
    "Bulan_Report", 
    "Status",
    "Nama Pencarian", 
    "Nama PN",
    "Domain", 
    "Nomor Perkara", 
    "Tanggal Register", 
    "Klasifikasi",
    "Pihak_Penggugat",     # Hasil parsing dari Para Pihak
    "Pihak_Tergugat",      # Hasil parsing dari Para Pihak
    "Para_Pihak_Original", # Opsional: menyimpan nilai asli untuk referensi
    "Lama Proses", 
    "Link", 
    "Timestamp", 
    "Keterangan"
]

st.sidebar.header("⚙️ Pengaturan")
st.sidebar.markdown("### Klasifikasi yang Dipertahankan:")
for k in RELEVANT_CLASSIFICATIONS:
    st.sidebar.markdown(f"- ✅ {k}")

st.sidebar.markdown("---")
st.sidebar.markdown("### Aturan Pemisahan Para Pihak:")
st.sidebar.markdown("""
- **Penggugat / Penuntut Umum** → masuk kolom `Pihak_Penggugat`
- **Tergugat / Terdakwa** → masuk kolom `Pihak_Tergugat`
""")
st.sidebar.markdown(f"**Total klasifikasi relevan:** {len(RELEVANT_CLASSIFICATIONS)}")


def parse_para_pihak(para_pihak_text):
    """
    Memisahkan teks Para Pihak menjadi Penggugat dan Tergugat
    
    Contoh input:
    - "Penuntut Umum:Slamet, SH. Terdakwa:CHANDRA WIJAYA PUTRA anak dari HENGKY WIJAYA"
    - "Penggugat:SUZY WINARTY Tergugat:TAN JEMMY SUGIARTO"
    """
    if pd.isna(para_pihak_text) or para_pihak_text == "":
        return "", ""
    
    text = str(para_pihak_text)
    
    # Pola untuk mencari Penggugat atau Penuntut Umum
    # Mencari pola "Penggugat:..." atau "Penuntut Umum:..."
    penggugat_pattern = r'(?:Penggugat|Penuntut Umum):([^.]*(?:\.(?!\s*(?:Tergugat|Terdakwa):)[^.]*)*)'
    tergugat_pattern = r'(?:Tergugat|Terdakwa):(.*?)(?:$|\.\s*(?:Penggugat|Penuntut Umum):)'
    
    # Cari Penggugat
    penggugat_match = re.search(penggugat_pattern, text, re.IGNORECASE)
    penggugat = penggugat_match.group(1).strip() if penggugat_match else ""
    
    # Cari Tergugat
    tergugat_match = re.search(tergugat_pattern, text, re.IGNORECASE)
    tergugat = tergugat_match.group(1).strip() if tergugat_match else ""
    
    # Jika pola regex di atas gagal, coba metode sederhana split
    if not penggugat and not tergugat:
        # Coba split berdasarkan kata kunci
        parts = re.split(r'\s+(?=Tergugat:|Terdakwa:)', text, maxsplit=1)
        if len(parts) == 2:
            # Bagian pertama adalah penggugat
            penggugat_part = parts[0]
            tergugat_part = parts[1]
            
            # Bersihkan label
            penggugat = re.sub(r'^(Penggugat:|Penuntut Umum:)', '', penggugat_part).strip()
            tergugat = re.sub(r'^(Tergugat:|Terdakwa:)', '', tergugat_part).strip()
    
    return penggugat, tergugat


def process_para_pihak_column(df):
    """Memproses kolom Para Pihak menjadi dua kolom terpisah"""
    if "Para Pihak" not in df.columns:
        st.warning("⚠️ Kolom 'Para Pihak' tidak ditemukan, kolom Pihak_Penggugat dan Pihak_Tergugat akan kosong")
        df["Pihak_Penggugat"] = ""
        df["Pihak_Tergugat"] = ""
        df["Para_Pihak_Original"] = ""
        return df
    
    # Simpan nilai asli
    df["Para_Pihak_Original"] = df["Para Pihak"]
    
    # Parse setiap baris
    parsed_data = df["Para Pihak"].apply(
        lambda x: pd.Series(parse_para_pihak(x), index=["Pihak_Penggugat", "Pihak_Tergugat"])
    )
    
    df["Pihak_Penggugat"] = parsed_data["Pihak_Penggugat"]
    df["Pihak_Tergugat"] = parsed_data["Pihak_Tergugat"]
    
    # Hapus kolom Para Pihak asli (sudah diganti dengan yang sudah dipisah)
    df = df.drop(columns=["Para Pihak"])
    
    return df


def load_excel_files(uploaded_files):
    """Load dan concat semua file Excel yang diupload"""
    all_dfs = []
    file_names = []
    
    for file in uploaded_files:
        try:
            df = pd.read_excel(file, engine='openpyxl')
            all_dfs.append(df)
            file_names.append(file.name)
        except Exception as e:
            st.error(f"Error membaca file {file.name}: {e}")
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        return combined_df, file_names
    return None, []


def filter_relevant_classifications(df):
    """Filter hanya baris dengan klasifikasi yang relevan"""
    if "Klasifikasi" not in df.columns:
        st.error("❌ Kolom 'Klasifikasi' tidak ditemukan dalam file!")
        return pd.DataFrame()
    
    # Case insensitive matching, bersihkan spasi
    df["Klasifikasi_clean"] = df["Klasifikasi"].astype(str).str.strip()
    
    filtered_df = df[df["Klasifikasi_clean"].isin(RELEVANT_CLASSIFICATIONS)]
    
    # Drop kolom bantuan
    filtered_df = filtered_df.drop(columns=["Klasifikasi_clean"])
    
    return filtered_df


def ensure_columns(df):
    """Pastikan semua kolom yang dibutuhkan ada (isi NaN jika tidak ada)"""
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    
    # Urutkan kolom sesuai OUTPUT_COLUMNS
    existing_cols = [col for col in OUTPUT_COLUMNS if col in df.columns]
    df = df[existing_cols]
    return df


def get_summary_stats(original_df, filtered_df):
    """Statistik ringkasan"""
    original_count = len(original_df)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    
    # Hitung per klasifikasi
    if filtered_count > 0 and "Klasifikasi" in filtered_df.columns:
        klasifikasi_counts = filtered_df["Klasifikasi"].value_counts().to_dict()
    else:
        klasifikasi_counts = {}
    
    # Hitung keberhasilan parsing Para Pihak
    parsing_success = 0
    if filtered_count > 0 and "Pihak_Penggugat" in filtered_df.columns:
        parsing_success = len(filtered_df[filtered_df["Pihak_Penggugat"] != ""])
    
    return {
        "original": original_count,
        "filtered": filtered_count,
        "removed": removed_count,
        "klasifikasi_counts": klasifikasi_counts,
        "parsing_success": parsing_success
    }


# Upload file
uploaded_files = st.file_uploader(
    "📂 Upload file Excel (multiple files)",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} file berhasil diupload")
    
    # Tombol proses
    if st.button("🚀 Proses Cleansing Data", type="primary"):
        with st.spinner("Memproses data..."):
            # Load semua file
            combined_df, file_names = load_excel_files(uploaded_files)
            
            if combined_df is not None and not combined_df.empty:
                # Tampilkan preview data awal
                st.subheader("📋 Preview Data Awal (Gabungan)")
                st.dataframe(combined_df.head(10), use_container_width=True)
                st.caption(f"Total baris awal: {len(combined_df)} baris")
                
                # Filter berdasarkan klasifikasi
                filtered_df = filter_relevant_classifications(combined_df)
                
                # Proses pemisahan kolom Para Pihak
                filtered_df = process_para_pihak_column(filtered_df)
                
                # Pastikan kolom lengkap
                filtered_df = ensure_columns(filtered_df)
                
                # Statistik
                stats = get_summary_stats(combined_df, filtered_df)
                
                # Tampilkan statistik
                st.subheader("📊 Statistik Hasil Cleansing")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Baris Awal", stats["original"])
                col2.metric("Baris Setelah Filter", stats["filtered"])
                col3.metric("Baris Terbuang", stats["removed"], delta=f"-{stats['removed']}" if stats['removed'] > 0 else "0")
                col4.metric("Berhasil Parse Para Pihak", stats["parsing_success"])
                
                # Tampilkan per klasifikasi yang lolos
                if stats["klasifikasi_counts"]:
                    st.subheader("📈 Distribusi Klasifikasi yang Lolos")
                    st.dataframe(
                        pd.DataFrame(stats["klasifikasi_counts"].items(), columns=["Klasifikasi", "Jumlah"]),
                        use_container_width=True
                    )
                
                # Contoh hasil parsing
                if not filtered_df.empty and stats["parsing_success"] > 0:
                    st.subheader("🔍 Contoh Hasil Pemisahan Kolom 'Para Pihak'")
                    
                    # Buat dataframe contoh
                    sample_df = filtered_df[["Pihak_Penggugat", "Pihak_Tergugat", "Para_Pihak_Original"]].head(5)
                    sample_df = sample_df.rename(columns={
                        "Para_Pihak_Original": "Original Para Pihak"
                    })
                    st.dataframe(sample_df, use_container_width=True)
                
                # Preview hasil
                if not filtered_df.empty:
                    # Tampilkan preview tanpa kolom original (agar lebih rapi)
                    preview_df = filtered_df.drop(columns=["Para_Pihak_Original"], errors='ignore')
                    st.subheader("✅ Preview Data Setelah Cleansing (10 baris pertama)")
                    st.dataframe(preview_df.head(10), use_container_width=True)
                    
                    # Tombol download
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, index=False, sheet_name="Cleansed_Data")
                    
                    output.seek(0)
                    
                    st.download_button(
                        label="📥 Download Compiled Excel",
                        data=output,
                        file_name="hasil_cleansing_perkara_keuangan.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success(f"✅ Cleansing selesai! {stats['filtered']} baris data dari {stats['original']} baris awal berhasil disimpan.")
                else:
                    st.warning("⚠️ Tidak ada baris data yang lolos filter klasifikasi. Periksa kembali isi kolom 'Klasifikasi' pada file Anda.")
            else:
                st.error("❌ Gagal memproses file. Pastikan file Excel memiliki format yang benar.")
else:
    st.info("📌 Silakan upload minimal 1 file Excel untuk memulai.")

# Footer
st.markdown("---")
st.caption("Aplikasi cleansing data perkara perusahaan - Filter klasifikasi keuangan & parsing Para Pihak")
