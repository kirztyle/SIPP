import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse

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
- Upload Excel berisi **Nama**
- Melakukan pencarian ke **banyak domain SIPP**
- Domain diambil dari `domain.xlsx`
- Output sesuai standar pelaporan
""")

uploaded_file = st.file_uploader("Upload Excel Nama", type=["xlsx"])

# =============================
# LOAD DOMAIN
# =============================
try:
    df_domain = pd.read_excel("domain.xlsx")
    df_domain.columns = [c.lower().strip() for c in df_domain.columns]
    domains = df_domain["domain"].dropna().unique()
except Exception as e:
    st.error(f"Gagal membaca domain.xlsx: {e}")
    st.stop()

domains = [normalize_domain(d) for d in domains]

st.info(f"{len(domains)} domain SIPP siap digunakan")

# =============================
# PROSES UTAMA
# =============================
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [c.lower().strip() for c in df.columns]

    if "nama" not in df.columns:
        st.error("Kolom 'nama' tidak ditemukan")
        st.stop()

    names = df["nama"].dropna().unique()
    st.success(f"{len(names)} nama siap diproses")

    if st.button("🚀 Mulai Scraping"):
        session = requests.Session()
        all_results = []

        total_task = len(names) * len(domains)
        progress = st.progress(0)
        status = st.empty()
        counter = 0

        for domain in domains:
            nama_pn = extract_nama_pn(domain)

            try:
                enc = get_enc_token(session, domain)
            except Exception as e:
                st.warning(f"Gagal ambil token di {domain}: {e}")
                continue

            for nama in names:
                counter += 1
                status.text(f"{nama} → {nama_pn}")

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

                progress.progress(counter / total_task)
                time.sleep(RATE_LIMIT)

        result_df = pd.DataFrame(all_results)

        st.subheader("📊 Hasil Akhir")
        st.dataframe(result_df, width='stretch')

        output = "hasil_multi_sipp.xlsx"
        result_df.to_excel(output, index=False)

        with open(output, "rb") as f:
            st.download_button(
                "⬇️ Download Excel",
                f,
                file_name=output
            )

        st.success("Scraping selesai dengan sukses")
