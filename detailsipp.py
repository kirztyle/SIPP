import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import io
from datetime import datetime

# Konfigurasi halaman
st.set_page_config(
    page_title="Scraper Data Perkara",
    page_icon="⚖️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stAlert {
        margin-top: 20px;
    }
    .dataframe {
        font-size: 12px;
    }
    .success-box {
        background-color: #d4edda;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("⚖️ Web Scraper Data Perkara")
st.markdown("Ambil data **Petitum** dan informasi perkara lainnya dari daftar link di file Excel")

# Sidebar
with st.sidebar:
    st.header("⚙️ Pengaturan")
    st.markdown("---")
    
    delay = st.slider(
        "Jeda antar request (detik)",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.5,
        help="Untuk menghindari rate limiting"
    )
    
    st.markdown("---")
    st.header("📋 Field yang diambil:")
    st.markdown("""
    - ✅ **Nama Pencarian** (dari file Excel)
    - ✅ **Pihak Tergugat** (dari file Excel)
    - ✅ Nomor Perkara
    - ✅ Tanggal Pendaftaran
    - ✅ Klasifikasi Perkara
    - ✅ Penggugat (hasil scraping)
    - ✅ Tergugat (hasil scraping)
    - ✅ **Petitum** (prioritas utama)
    - ✅ Nilai Sengketa
    - ✅ Status Publikasi
    """)
    
    st.markdown("---")
    st.info("💡 **Catatan:** Kolom 'Nama Pencarian' dan 'Pihak_Tergugat' akan digabungkan dengan hasil scraping")

# Function untuk scraping satu URL
def scrape_perkara(url, headers):
    """Scrape data perkara dari satu URL"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Dictionary untuk menyimpan hasil
        data = {
            'URL': url,
            'Nomor Perkara': '',
            'Tanggal Pendaftaran': '',
            'Klasifikasi Perkara': '',
            'Penggugat': '',
            'Tergugat_Scraping': '',
            'Petitum': '',
            'Nilai Sengketa': '',
            'Pihak Dipublikasikan': '',
            'Status': 'Sukses',
            'Error Message': ''
        }
        
        # Cari tabel utama
        table = soup.find('table', id='infoPerkara')
        if not table:
            data['Status'] = 'Gagal'
            data['Error Message'] = 'Tabel infoPerkara tidak ditemukan'
            return data
        
        # Parse baris-baris tabel
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                label_cell = cells[0]
                value_cell = cells[1]
                
                label = label_cell.get_text(strip=True).lower()
                value = value_cell.get_text(strip=True)
                
                if 'nomor perkara' in label:
                    data['Nomor Perkara'] = value
                elif 'tanggal pendaftaran' in label:
                    data['Tanggal Pendaftaran'] = value
                elif 'klasifikasi perkara' in label:
                    data['Klasifikasi Perkara'] = value
                elif 'penggugat' in label:
                    # Ambil nama penggugat dari tabel dalam
                    data['Penggugat'] = extract_names_from_inner_table(value_cell)
                elif 'tergugat' in label and 'kuasa' not in label:
                    data['Tergugat_Scraping'] = extract_names_from_inner_table(value_cell)
                elif 'petitum' in label:
                    data['Petitum'] = clean_petitum(value)
                elif 'nilai sengketa' in label:
                    data['Nilai Sengketa'] = value
                elif 'pihak dipublikasikan' in label:
                    data['Pihak Dipublikasikan'] = value
        
        return data
        
    except requests.exceptions.RequestException as e:
        return {
            'URL': url,
            'Nomor Perkara': '',
            'Tanggal Pendaftaran': '',
            'Klasifikasi Perkara': '',
            'Penggugat': '',
            'Tergugat_Scraping': '',
            'Petitum': '',
            'Nilai Sengketa': '',
            'Pihak Dipublikasikan': '',
            'Status': 'Gagal',
            'Error Message': str(e)
        }
    except Exception as e:
        return {
            'URL': url,
            'Nomor Perkara': '',
            'Tanggal Pendaftaran': '',
            'Klasifikasi Perkara': '',
            'Penggugat': '',
            'Tergugat_Scraping': '',
            'Petitum': '',
            'Nilai Sengketa': '',
            'Pihak Dipublikasikan': '',
            'Status': 'Gagal',
            'Error Message': f"Error: {str(e)}"
        }

def extract_names_from_inner_table(value_cell):
    """Extract nama dari tabel di dalam (penggugat/tergugat)"""
    inner_table = value_cell.find('table')
    if not inner_table:
        return value_cell.get_text(strip=True)
    
    names = []
    rows = inner_table.find_all('tr')
    for row in rows[1:]:  # skip header
        cells = row.find_all('td')
        if len(cells) >= 2:
            name = cells[1].get_text(strip=True)
            if name:
                names.append(name)
    
    return '; '.join(names) if names else '-'

def clean_petitum(text):
    """Bersihkan teks petitum"""
    # Hapus extra whitespace
    text = ' '.join(text.split())
    # Pisahkan poin-poin dengan newline untuk readability
    text = text.replace(';<br>', ';\n').replace('<br>', '\n')
    return text

def process_urls(df, url_column, delay, progress_bar, status_text):
    """Proses multiple URLs dengan menggabungkan data dari Excel"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    total_rows = len(df)
    
    for i, (idx, row) in enumerate(df.iterrows()):
        url = str(row[url_column]).strip()
        
        status_text.text(f"Memproses {i+1}/{total_rows}: {url[:80]}...")
        
        # Tambahkan http:// jika tidak ada protocol
        if not url.startswith('http'):
            url = 'http://' + url
        
        # Scrape data
        scraped_data = scrape_perkara(url, headers)
        
        # Gabungkan dengan data dari Excel
        final_data = {
            'Nama Pencarian': row.get('Nama Pencarian', ''),
            'Pihak_Tergugat': row.get('Pihak_Tergugat', ''),
            'URL': url,
            'Nomor Perkara': scraped_data.get('Nomor Perkara', ''),
            'Tanggal Pendaftaran': scraped_data.get('Tanggal Pendaftaran', ''),
            'Klasifikasi Perkara': scraped_data.get('Klasifikasi Perkara', ''),
            'Penggugat': scraped_data.get('Penggugat', ''),
            'Tergugat_Scraping': scraped_data.get('Tergugat_Scraping', ''),
            'Petitum': scraped_data.get('Petitum', ''),
            'Nilai Sengketa': scraped_data.get('Nilai Sengketa', ''),
            'Pihak Dipublikasikan': scraped_data.get('Pihak Dipublikasikan', ''),
            'Status': scraped_data.get('Status', 'Gagal'),
            'Error Message': scraped_data.get('Error Message', '')
        }
        
        results.append(final_data)
        
        # Update progress
        progress_bar.progress((i + 1) / total_rows)
        
        # Delay
        if i < total_rows - 1:
            time.sleep(delay)
    
    return results

# Main app
tab1, tab2, tab3 = st.tabs(["📁 Upload & Scrape", "📊 Hasil Scraping", "ℹ️ Panduan"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload file Excel (format .xlsx atau .xls)",
            type=['xlsx', 'xls'],
            help="File HARUS memiliki kolom: 'Nama Pencarian', 'Pihak_Tergugat', dan kolom URL"
        )
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ Berhasil membaca file: {len(df)} baris data")
                
                # Cek kolom yang diperlukan
                required_columns = ['Nama Pencarian', 'Pihak_Tergugat']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    st.error(f"❌ File Excel HARUS memiliki kolom: {', '.join(missing_columns)}")
                    st.info("📌 Contoh format file yang benar:")
                    st.code("| Nama Pencarian | Pihak_Tergugat | URL |")
                    st.stop()
                
                # Deteksi kolom URL
                possible_url_columns = ['url', 'URL', 'link', 'Link', 'LINK', 'alamat', 'website']
                url_column = None
                
                for col in possible_url_columns:
                    if col in df.columns:
                        url_column = col
                        break
                
                if url_column is None:
                    st.warning("⚠️ Tidak menemukan kolom URL/Link. Silakan pilih kolom yang berisi URL:")
                    url_column = st.selectbox("Pilih kolom URL", df.columns)
                else:
                    st.info(f"📌 Menggunakan kolom: **{url_column}**")
                
                # Preview data
                with st.expander("Preview data Excel (10 baris pertama)"):
                    st.dataframe(df[required_columns + [url_column]].head(10))
                
                # Statistik data
                st.info(f"""
                📊 **Statistik Data:**
                - Total baris: {len(df)}
                - Nama Pencarian tidak kosong: {(df['Nama Pencarian'].notna() & (df['Nama Pencarian'] != '')).sum()}
                - Pihak_Tergugat tidak kosong: {(df['Pihak_Tergugat'].notna() & (df['Pihak_Tergugat'] != '')).sum()}
                - URL tidak kosong: {(df[url_column].notna() & (df[url_column] != '')).sum()}
                """)
                
                # Tombol start scraping
                if st.button("🚀 Mulai Scraping", type="primary", use_container_width=True):
                    # Filter baris dengan URL valid
                    valid_rows = df[df[url_column].notna() & (df[url_column] != '')]
                    valid_rows = valid_rows.reset_index(drop=True)
                    
                    if len(valid_rows) == 0:
                        st.error("❌ Tidak ada URL valid untuk diproses!")
                        st.stop()
                    
                    st.info(f"📊 Akan memproses {len(valid_rows)} URL dari total {len(df)} baris")
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Proses scraping
                    results = process_urls(valid_rows, url_column, delay, progress_bar, status_text)
                    
                    # Simpan ke session state
                    st.session_state['results'] = results
                    st.session_state['df_results'] = pd.DataFrame(results)
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    sukses_count = len([r for r in results if r['Status'] == 'Sukses'])
                    gagal_count = len([r for r in results if r['Status'] == 'Gagal'])
                    
                    st.success(f"✅ Scraping selesai! {sukses_count} berhasil, {gagal_count} gagal")
                    
                    # Auto switch ke tab hasil
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Gagal membaca file: {str(e)}")

with tab2:
    if 'df_results' in st.session_state and not st.session_state['df_results'].empty:
        df_results = st.session_state['df_results']
        
        # Statistik
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total URL", len(df_results))
        with col2:
            sukses = len(df_results[df_results['Status'] == 'Sukses'])
            st.metric("Berhasil", sukses, delta=f"{sukses/len(df_results)*100:.0f}%")
        with col3:
            gagal = len(df_results[df_results['Status'] == 'Gagal'])
            st.metric("Gagal", gagal)
        with col4:
            with_petitum = len(df_results[df_results['Petitum'] != ''])
            st.metric("Dapat Petitum", with_petitum)
        with col5:
            match_tergugat = len(df_results[
                (df_results['Pihak_Tergugat'] != '') & 
                (df_results['Tergugat_Scraping'] != '')
            ])
            st.metric("Tergugat Terisi", match_tergugat)
        
        st.markdown("---")
        
        # Filter
        filter_status = st.multiselect(
            "Filter Status",
            options=['Sukses', 'Gagal'],
            default=['Sukses']
        )
        
        search = st.text_input("🔍 Cari berdasarkan Nama Pencarian atau Nomor Perkara", "")
        
        filtered_df = df_results[df_results['Status'].isin(filter_status)]
        
        if search:
            filtered_df = filtered_df[
                filtered_df['Nama Pencarian'].str.contains(search, case=False, na=False) |
                filtered_df['Nomor Perkara'].str.contains(search, case=False, na=False)
            ]
        
        st.subheader(f"📋 Hasil Scraping ({len(filtered_df)} data)")
        
        # Tampilkan data dalam bentuk tabel ringkas
        display_df = filtered_df[['Nama Pencarian', 'Pihak_Tergugat', 'Nomor Perkara', 'Tergugat_Scraping', 'Status']].copy()
        st.dataframe(display_df, use_container_width=True)
        
        # Detail per baris dengan expander
        st.markdown("---")
        st.subheader("📄 Detail Lengkap Per Data")
        
        for idx, row in filtered_df.iterrows():
            with st.expander(f"📌 {row['Nama Pencarian']} - {row['Nomor Perkara'] if row['Nomor Perkara'] else 'No. Perkara Tidak Diketahui'} - {row['Status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**📋 Data dari File Excel:**")
                    st.write(f"**Nama Pencarian:** {row['Nama Pencarian']}")
                    st.write(f"**Pihak_Tergugat:** {row['Pihak_Tergugat']}")
                    st.write(f"**URL:** {row['URL']}")
                    
                    st.markdown("**⚖️ Data Hasil Scraping:**")
                    st.write(f"**Nomor Perkara:** {row['Nomor Perkara']}")
                    st.write(f"**Tanggal Pendaftaran:** {row['Tanggal Pendaftaran']}")
                    st.write(f"**Klasifikasi Perkara:** {row['Klasifikasi Perkara']}")
                
                with col2:
                    st.write(f"**Penggugat:**")
                    st.text_area("", row['Penggugat'], height=100, key=f"penggugat_{idx}", label_visibility="collapsed")
                    
                    st.write(f"**Tergugat (Scraping):**")
                    st.text_area("", row['Tergugat_Scraping'], height=100, key=f"tergugat_{idx}", label_visibility="collapsed")
                
                st.markdown("**📜 PETITUM:**")
                st.text_area("", row['Petitum'], height=200, key=f"petitum_{idx}", label_visibility="collapsed")
                
                if row['Status'] == 'Gagal':
                    st.error(f"❌ Error: {row['Error Message']}")
                
                # Perbandingan Tergugat
                if row['Pihak_Tergugat'] and row['Tergugat_Scraping']:
                    if row['Pihak_Tergugat'].lower() in row['Tergugat_Scraping'].lower():
                        st.success("✅ Pihak_Tergugat cocok dengan hasil scraping")
                    else:
                        st.warning("⚠️ Pihak_Tergugat berbeda dengan hasil scraping")
        
        # Download buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_results.to_excel(writer, index=False, sheet_name='Hasil Scraping')
            
            st.download_button(
                label="📥 Download Excel",
                data=output.getvalue(),
                file_name=f"hasil_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # Download CSV
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"hasil_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            # Download hanya kolom tertentu
            summary_df = df_results[['Nama Pencarian', 'Pihak_Tergugat', 'Nomor Perkara', 'Tergugat_Scraping', 'Petitum', 'Status']]
            summary_output = io.BytesIO()
            with pd.ExcelWriter(summary_output, engine='openpyxl') as writer:
                summary_df.to_excel(writer, index=False, sheet_name='Ringkasan')
            
            st.download_button(
                label="📥 Download Ringkasan",
                data=summary_output.getvalue(),
                file_name=f"ringkasan_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("👈 Silakan upload file Excel dan mulai scraping di tab 'Upload & Scrape'")

with tab3:
    st.markdown("""
    ## 📖 Panduan Penggunaan
    
    ### Format File Excel yang Diperlukan:
    
    File Excel HARUS memiliki kolom berikut:
    
    | Nama Pencarian | Pihak_Tergugat | URL |
    |----------------|----------------|-----|
    | PT. Mandiri Utama | PT. Mandiri Utama Finance | https://sipp.pn-blitar.go.id/detil/... |
    | Safarul Anam | Safarul Anam, S.H. | https://sipp.pn-blitar.go.id/detil/... |
    
    ### Kolom yang wajib ada:
    1. **Nama Pencarian** - Nama atau keyword untuk pencarian
    2. **Pihak_Tergugat** - Data tergugat dari file Excel (akan dibandingkan dengan hasil scraping)
    3. **URL** atau **Link** - Alamat website detail perkara
    
    ### Langkah-langkah:
    1. **Siapkan file Excel** dengan 3 kolom wajib di atas
    2. **Upload file** melalui tab "Upload & Scrape"
    3. **Pilih kolom URL** (jika tidak terdeteksi otomatis)
    4. **Klik tombol "Mulai Scraping"**
    5. **Tunggu proses selesai** (ada progress bar)
    6. **Lihat hasil** di tab "Hasil Scraping"
    
    ### Data yang dihasilkan:
    
    #### Dari file Excel:
    - Nama Pencarian
    - Pihak_Tergugat
    
    #### Dari hasil scraping:
    - Nomor Perkara
    - Tanggal Pendaftaran
    - Klasifikasi Perkara
    - Penggugat
    - Tergugat_Scraping
    - **Petitum** (utama)
    - Nilai Sengketa
    - Status Publikasi
    
    ### Fitur Tambahan:
    - ✅ Perbandingan otomatis antara Pihak_Tergugat (Excel) dengan Tergugat_Scraping
    - ✅ Pencarian berdasarkan Nama Pencarian atau Nomor Perkara
    - ✅ Filter berdasarkan status sukses/gagal
    - ✅ Download hasil dalam 3 format (Excel lengkap, CSV, Ringkasan)
    
    ### Catatan Penting:
    ⚠️ **Website yang di-scrape harus mendukung requests (tidak memerlukan JavaScript)**
    ⚠️ **Gunakan jeda antar request untuk menghindari pemblokiran IP**
    ⚠️ **Hormati robots.txt dan kebijakan website terkait**
    
    ### Troubleshooting:
    - **File tidak bisa diupload**: Pastikan format .xlsx atau .xls dan memiliki kolom yang benar
    - **Gagal koneksi**: Periksa URL dan koneksi internet
    - **Petitum kosong**: Struktur HTML mungkin berbeda dari contoh
    - **Rate limited**: Tingkatkan jeda antar request di sidebar
    """)

st.markdown("---")
st.markdown("⚖️ Dibuat dengan ❤️ - Scraper Data Perkara dengan Excel Input")
