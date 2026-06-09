import streamlit as st
import pandas as pd
import io
from pathlib import Path

# Konfigurasi halaman
st.set_page_config(
    page_title="Cleansing Data Perkara Perusahaan",
    page_icon="📊",
    layout="wide"
)

# Judul
st.title("📊 Aplikasi Cleansing Data Perkara Perusahaan")
st.markdown("""
Upload multiple file Excel, sistem akan **memfilter** hanya baris dengan klasifikasi yang **relevan terhadap masalah keuangan perusahaan**.
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

# Kolom yang dipertahankan (urutan sesuai permintaan)
OUTPUT_COLUMNS = [
    "CIF", "Bulan_Report", "Status", "Nama Pencarian", "Nama PN",
    "Domain", "Nomor Perkara", "Tanggal Register", "Klasifikasi",
    "Para Pihak", "Status", "Lama Proses", "Link", "Timestamp", "Keterangan"
]

st.sidebar.header("⚙️ Pengaturan")
st.sidebar.markdown("### Klasifikasi yang Dipertahankan:")
for k in RELEVANT_CLASSIFICATIONS:
    st.sidebar.markdown(f"- ✅ {k}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Total klasifikasi relevan:** {len(RELEVANT_CLASSIFICATIONS)}")


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
    
    return {
        "original": original_count,
        "filtered": filtered_count,
        "removed": removed_count,
        "klasifikasi_counts": klasifikasi_counts
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
                
                # Pastikan kolom lengkap
                filtered_df = ensure_columns(filtered_df)
                
                # Statistik
                stats = get_summary_stats(combined_df, filtered_df)
                
                # Tampilkan statistik
                st.subheader("📊 Statistik Hasil Cleansing")
                col1, col2, col3 = st.columns(3)
                col1.metric("Baris Awal", stats["original"])
                col2.metric("Baris Setelah Filter", stats["filtered"])
                col3.metric("Baris Terbuang", stats["removed"], delta=f"-{stats['removed']}" if stats['removed'] > 0 else "0")
                
                # Tampilkan per klasifikasi yang lolos
                if stats["klasifikasi_counts"]:
                    st.subheader("📈 Distribusi Klasifikasi yang Lolos")
                    st.dataframe(
                        pd.DataFrame(stats["klasifikasi_counts"].items(), columns=["Klasifikasi", "Jumlah"]),
                        use_container_width=True
                    )
                
                # Preview hasil
                if not filtered_df.empty:
                    st.subheader("✅ Preview Data Setelah Cleansing (10 baris pertama)")
                    st.dataframe(filtered_df.head(10), use_container_width=True)
                    
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
st.caption("Aplikasi cleansing data perkara perusahaan - Filter klasifikasi yang terkait dengan masalah keuangan perusahaan.")
