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
    - ✅ Nomor Perkara
    - ✅ Tanggal Pendaftaran
    - ✅ Klasifikasi Perkara
    - ✅ Penggugat
    - ✅ Tergugat
    - ✅ **Petitum** (prioritas)
    - ✅ Nilai Sengketa
    - ✅ Status Publikasi
    """)

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
            'Tergugat': '',
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
                    data['Tergugat'] = extract_names_from_inner_table(value_cell)
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
            'Tergugat': '',
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
            'Tergugat': '',
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

def process_urls(url_list, delay, progress_bar, status_text):
    """Proses multiple URLs dengan progress"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for i, url in enumerate(url_list):
        status_text.text(f"Memproses: {url[:80]}...")
        
        # Tambahkan http:// jika tidak ada protocol
        if not url.startswith('http'):
            url = 'http://' + url
        
        result = scrape_perkara(url, headers)
        results.append(result)
        
        # Update progress
        progress_bar.progress((i + 1) / len(url_list))
        
        # Delay
        if i < len(url_list) - 1:
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
            help="File harus memiliki kolom berisi URL (default: 'URL' atau 'Link')"
        )
        
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ Berhasil membaca file: {len(df)} baris data")
                
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
                with st.expander("Preview data Excel"):
                    st.dataframe(df.head(10))
                
                # Tombol start scraping
                if st.button("🚀 Mulai Scraping", type="primary", use_container_width=True):
                    # Ambil list URL
                    url_list = df[url_column].dropna().tolist()
                    url_list = [str(url).strip() for url in url_list]
                    
                    st.info(f"📊 Akan memproses {len(url_list)} URL")
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Proses scraping
                    results = process_urls(url_list, delay, progress_bar, status_text)
                    
                    # Simpan ke session state
                    st.session_state['results'] = results
                    st.session_state['df_results'] = pd.DataFrame(results)
                    
                    progress_bar.empty()
                    status_text.empty()
                    st.success(f"✅ Scraping selesai! {len([r for r in results if r['Status']=='Sukses'])} berhasil, {len([r for r in results if r['Status']=='Gagal'])} gagal")
                    
                    # Auto switch ke tab hasil
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Gagal membaca file: {str(e)}")

with tab2:
    if 'df_results' in st.session_state and not st.session_state['df_results'].empty:
        df_results = st.session_state['df_results']
        
        # Statistik
        col1, col2, col3, col4 = st.columns(4)
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
        
        st.markdown("---")
        
        # Filter
        filter_status = st.multiselect(
            "Filter Status",
            options=['Sukses', 'Gagal'],
            default=['Sukses']
        )
        
        filtered_df = df_results[df_results['Status'].isin(filter_status)]
        
        # Tampilkan data
        st.subheader("📋 Hasil Scraping")
        
        # Pilih kolom yang ditampilkan
        display_columns = ['Nomor Perkara', 'Klasifikasi Perkara', 'Penggugat', 'Tergugat', 'Status']
        
        # Tampilkan dengan expandable Petitum
        for idx, row in filtered_df.iterrows():
            with st.expander(f"📌 {row['Nomor Perkara'] if row['Nomor Perkara'] else 'No. Perkara Tidak Diketahui'} - {row['Status']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Nomor Perkara:**")
                    st.write(row['Nomor Perkara'])
                    st.markdown("**Tanggal Pendaftaran:**")
                    st.write(row['Tanggal Pendaftaran'])
                    st.markdown("**Klasifikasi:**")
                    st.write(row['Klasifikasi Perkara'])
                with col2:
                    st.markdown("**Penggugat:**")
                    st.write(row['Penggugat'][:200] + "..." if len(row['Penggugat']) > 200 else row['Penggugat'])
                    st.markdown("**Tergugat:**")
                    st.write(row['Tergugat'][:200] + "..." if len(row['Tergugat']) > 200 else row['Tergugat'])
                
                st.markdown("**📜 PETITUM:**")
                st.text_area("", row['Petitum'], height=200, key=f"petitum_{idx}")
                
                if row['Status'] == 'Gagal':
                    st.error(f"Error: {row['Error Message']}")
                
                st.markdown(f"🔗 [Buka URL]({row['URL']})")
        
        # Download buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        
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
    else:
        st.info("👈 Silakan upload file Excel dan mulai scraping di tab 'Upload & Scrape'")

with tab3:
    st.markdown("""
    ## 📖 Panduan Penggunaan
    
    ### Langkah-langkah:
    1. **Siapkan file Excel** dengan kolom berisi daftar URL (contoh: kolom 'URL' atau 'Link')
    2. **Upload file** melalui tab "Upload & Scrape"
    3. **Pilih kolom URL** (jika tidak terdeteksi otomatis)
    4. **Klik tombol "Mulai Scraping"**
    5. **Tunggu proses selesai** (akan ada progress bar)
    6. **Lihat hasil** di tab "Hasil Scraping"
    7. **Download hasil** dalam format Excel atau CSV
    
    ### Format File Excel yang didukung:
    - .xlsx
    - .xls
    
    ### Contoh struktur file:
    
    | URL | Keterangan |
    |-----|------------|
    | https://sipp.pn-blitar.go.id/detil/172/Pdt.G/2025/PN_Blt | Perkara 1 |
    | https://sipp.pn-blitar.go.id/detil/... | Perkara 2 |
    
    ### Data yang diambil:
    - Nomor Perkara
    - Tanggal Pendaftaran
    - Klasifikasi Perkara
    - Penggugat
    - Tergugat
    - **Petitum** (utama)
    - Nilai Sengketa
    - Status Publikasi
    
    ### Catatan Penting:
    ⚠️ **Website yang di-scrape harus mendukung requests (tidak memerlukan JavaScript)**
    ⚠️ **Gunakan jeda antar request untuk menghindari pemblokiran IP**
    ⚠️ **Hormati robots.txt dan kebijakan website terkait**
    
    ### Troubleshooting:
    - **Gagal koneksi**: Periksa URL dan koneksi internet
    - **Petitum kosong**: Struktur HTML mungkin berbeda dari contoh
    - **Rate limited**: Tingkatkan jeda antar request
    """)

st.markdown("---")
st.markdown("⚖️ Dibuat dengan ❤️ untuk kebutuhan scraping data perkara")
