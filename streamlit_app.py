import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import io

# =============================
# KONFIGURASI
# =============================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StreamlitScraper/1.0)"
}

RATE_LIMIT = 1.5  # detik

# =============================
# UTILITAS
# =============================
def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if not domain.startswith("http"):
        domain = "https://" + domain
    return domain.rstrip("/")

def extract_nama_pn(domain: str) -> str:
    """
    https://sipp.pn-bandung.go.id -> BANDUNG
    """
    match = re.search(r"pn-([a-z\-]+)\.go\.id", domain)
    if match:
        return match.group(1).upper()
    return "UNKNOWN"

# =============================
# AMBIL TOKEN enc
# =============================
def get_enc_token(session, base_domain):
    url = f"{base_domain}/list_perkara"
    res = session.get(url, headers=HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    enc = soup.find("input", {"name": "enc"})

    if not enc:
        raise ValueError("Token enc tidak ditemukan")

    return enc["value"]

# =============================
# SCRAPING PER NAMA & DOMAIN
# =============================
def search_sipp(session, base_domain, enc, nama, nama_pn):
    search_url = f"{base_domain}/list_perkara/search"

    payload = {
        "search_keyword": nama,
        "enc": enc
    }

    res = session.post(search_url, data=payload, headers=HEADERS, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")

    results = []

    if not table:
        return results

    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]

        if len(cols) >= 6:
            results.append({
                "Nama": nama,
                "Nomor Perkara": cols[0],
                "Jenis Perkara": cols[1],
                "Para Pihak": cols[2],
                "Tanggal Register": cols[3],
                "Status": cols[4],
                "Tanggal Status": cols[5],
                "Nama PN": nama_pn
            })

    return results

# =============================
# STREAMLIT UI
# =============================
st.set_page_config(page_title="Multi SIPP Scraper", layout="wide")
st.title("📄 Multi Domain SIPP Scraper")

st.markdown("""
Aplikasi ini:
- Upload **dua file Excel**:
  1. **File Nama** (berisi daftar nama yang akan dicari)
  2. **File Domain** (berisi daftar domain SIPP yang akan di-scrape)
- Melakukan pencarian ke **banyak domain SIPP**
- Output sesuai standar pelaporan
""")

# =============================
# UPLOAD FILE DOMAIN
# =============================
st.subheader("1️⃣ Upload File Domain")
st.markdown("File Excel harus memiliki kolom **'domain'** (huruf kecil)")

uploaded_domain_file = st.file_uploader(
    "Upload domain.xlsx",
    type=["xlsx"],
    key="domain_uploader"
)

domains = []
if uploaded_domain_file:
    try:
        df_domain = pd.read_excel(uploaded_domain_file)
        df_domain.columns = [c.lower().strip() for c in df_domain.columns]
        
        if "domain" not in df_domain.columns:
            st.error("Kolom 'domain' tidak ditemukan dalam file domain.xlsx")
            st.write("Kolom yang ditemukan:", list(df_domain.columns))
        else:
            domains = df_domain["domain"].dropna().unique()
            domains = [normalize_domain(d) for d in domains]
            st.success(f"{len(domains)} domain SIPP berhasil dimuat")
            
            # Tampilkan preview domain
            with st.expander("📋 Lihat Daftar Domain"):
                st.dataframe(pd.DataFrame({"Domain": domains}))
    except Exception as e:
        st.error(f"Gagal membaca file domain.xlsx: {e}")
        st.stop()

# =============================
# UPLOAD FILE NAMA
# =============================
st.subheader("2️⃣ Upload File Nama")
st.markdown("File Excel harus memiliki kolom **'nama'** (huruf kecil)")

uploaded_nama_file = st.file_uploader(
    "Upload Excel Nama",
    type=["xlsx"],
    key="nama_uploader"
)

names = []
if uploaded_nama_file:
    try:
        df = pd.read_excel(uploaded_nama_file)
        df.columns = [c.lower().strip() for c in df.columns]
        
        if "nama" not in df.columns:
            st.error("Kolom 'nama' tidak ditemukan dalam file nama")
            st.write("Kolom yang ditemukan:", list(df.columns))
            st.stop()
        
        names = df["nama"].dropna().unique()
        st.success(f"{len(names)} nama siap diproses")
        
        # Tampilkan preview nama
        with st.expander("👥 Lihat Daftar Nama"):
            st.dataframe(pd.DataFrame({"Nama": names}))
    except Exception as e:
        st.error(f"Gagal membaca file nama: {e}")
        st.stop()

# =============================
# PROSES UTAMA
# =============================
if domains and names and st.button("🚀 Mulai Scraping", type="primary"):
    if len(domains) == 0:
        st.error("Tidak ada domain yang valid")
        st.stop()
    
    if len(names) == 0:
        st.error("Tidak ada nama yang valid")
        st.stop()
    
    session = requests.Session()
    all_results = []

    total_task = len(names) * len(domains)
    
    # Buat progress bar dan status
    progress_bar = st.progress(0)
    status_text = st.empty()
    counter = 0
    
    # Tambahkan log area
    log_area = st.empty()
    log_messages = []
    
    # Container untuk hasil real-time
    results_container = st.container()
    
    for domain_idx, domain in enumerate(domains, 1):
        nama_pn = extract_nama_pn(domain)
        
        # Log domain yang sedang diproses
        log_messages.append(f"🔗 Domain {domain_idx}/{len(domains)}: {domain}")
        log_area.markdown("\n".join(log_messages[-10:]))  # Tampilkan 10 log terakhir
        
        try:
            status_text.text(f"Mengambil token dari {nama_pn}...")
            enc = get_enc_token(session, domain)
            log_messages.append(f"   ✅ Token berhasil diambil")
        except Exception as e:
            log_messages.append(f"   ❌ Gagal ambil token: {e}")
            log_area.markdown("\n".join(log_messages[-10:]))
            continue
        
        for name_idx, nama in enumerate(names, 1):
            counter += 1
            status_text.text(f"Memproses: {nama} → {nama_pn} ({counter}/{total_task})")
            
            try:
                results = search_sipp(
                    session=session,
                    base_domain=domain,
                    enc=enc,
                    nama=nama,
                    nama_pn=nama_pn
                )

                if results:
                    all_results.extend(results)
                    log_messages.append(f"   ✅ {nama}: {len(results)} hasil ditemukan")
                else:
                    all_results.append({
                        "Nama": nama,
                        "Nomor Perkara": "TIDAK DITEMUKAN",
                        "Jenis Perkara": "-",
                        "Para Pihak": "-",
                        "Tanggal Register": "-",
                        "Status": "-",
                        "Tanggal Status": "-",
                        "Nama PN": nama_pn
                    })
                    log_messages.append(f"   ⚠️ {nama}: Tidak ditemukan")

            except Exception as e:
                all_results.append({
                    "Nama": nama,
                    "Nomor Perkara": "ERROR",
                    "Jenis Perkara": str(e),
                    "Para Pihak": "-",
                    "Tanggal Register": "-",
                    "Status": "-",
                    "Tanggal Status": "-",
                    "Nama PN": nama_pn
                })
                log_messages.append(f"   ❌ {nama}: Error - {str(e)[:50]}...")

            # Update progress bar
            progress_bar.progress(counter / total_task)
            
            # Update log setiap 5 proses
            if counter % 5 == 0 or counter == total_task:
                log_area.markdown("\n".join(log_messages[-10:]))
            
            time.sleep(RATE_LIMIT)
    
    # Tampilkan hasil akhir
    st.success("✅ Scraping selesai!")
    
    if all_results:
        result_df = pd.DataFrame(all_results)
        
        st.subheader("📊 Hasil Akhir")
        
        # Tampilkan statistik
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Data", len(result_df))
        with col2:
            found = len(result_df[result_df["Nomor Perkara"] != "TIDAK DITEMUKAN"])
            st.metric("Data Ditemukan", found)
        with col3:
            error = len(result_df[result_df["Nomor Perkara"] == "ERROR"])
            st.metric("Error", error)
        
        # Tampilkan dataframe
        st.dataframe(result_df, use_container_width=True)
        
        # Download button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            result_df.to_excel(writer, index=False, sheet_name='Hasil_Scraping')
        
        output.seek(0)
        
        st.download_button(
            label="⬇️ Download Excel Hasil",
            data=output,
            file_name="hasil_multi_sipp.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        # Tampilkan data per PN
        with st.expander("📈 Statistik per Pengadilan Negeri"):
            pn_stats = result_df.groupby("Nama PN").agg({
                "Nama": "count",
                "Nomor Perkara": lambda x: (x != "TIDAK DITEMUKAN").sum()
            }).rename(columns={"Nama": "Total Pencarian", "Nomor Perkara": "Ditemukan"})
            pn_stats["Success Rate"] = (pn_stats["Ditemukan"] / pn_stats["Total Pencarian"] * 100).round(1)
            st.dataframe(pn_stats)
    else:
        st.warning("Tidak ada data yang berhasil di-scrape")
