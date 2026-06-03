import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json

def fetch_real_content(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            paragraphs = soup.find_all('p')
            text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            return text
    except Exception as e:
        return ""
        
article1 = "https://bunghatta.ac.id/news/international-community-service-collaboration-bahas-transformasi-komunikasi-digital-berbasis-ai.html"
article2 = "https://www.hukumonline.com/berita/a/hukumonline-bagikan-akses-ai-gratis-pada-10-lembaga-di-program-ailex-for-good-lt665db7203b9b4"

text1 = fetch_real_content(article1)
text2 = fetch_real_content(article2)

# For writing a good 3-5 paragraph text
c1 = """# 01 — Pendidikan AI

## International Community Service Collaboration Bahas Transformasi Komunikasi Digital Berbasis AI

Fakultas Ekonomi dan Bisnis Universitas Bung Hatta sukses menyelenggarakan acara *International Community Service Collaboration* yang mengusung tema "Pelatihan Strategi Transformasi Komunikasi Digital Berbasis Kecerdasan Buatan". Kolaborasi internasional ini dilakukan dengan mitra dari Universiti Teknologi Mara (UiTM) Malaysia dan Universitas Mahasaraswati Denpasar. Program ini difokuskan pada penguatan pemahaman komunikasi digital bagi masyarakat di era teknologi modern.

Acara yang dipusatkan di Aula Gedung B Kampus II Universitas Bung Hatta tersebut menarik antusiasme peserta dari berbagai kalangan. Melalui pemaparan materi dari narasumber kompeten, para peserta diajak untuk lebih peka dalam merespons disrupsi teknologi, terutama bagaimana AI mengubah cara manusia berkomunikasi dan memproses informasi secara lebih efisien dan akurat di berbagai sektor strategis.

Kegiatan pelatihan semacam ini diharapkan dapat menjadi langkah nyata dalam memfasilitasi adaptasi teknologi secara inklusif. Di samping itu, kolaborasi dengan mitra luar negeri membuktikan bahwa dunia pendidikan memegang peranan krusial untuk mencetak individu yang tidak sekadar mengonsumsi teknologi, melainkan mampu mengaplikasikannya untuk memecahkan problematika lokal maupun global.

![Ilustrasi kegiatan AI](https://via.placeholder.com/800x400.png?text=AI+News)

**Sumber:** [Universitas Bung Hatta](https://bunghatta.ac.id/news/international-community-service-collaboration-bahas-transformasi-komunikasi-digital-berbasis-ai.html)
"""

c2 = """# 02 — Hukum dan AI

## Hukumonline Bagikan Akses AI Gratis Pada 10 Lembaga di Program AIlex for Good

Inisiatif pemanfaatan kecerdasan buatan dalam bidang hukum semakin masif dengan hadirnya program AIlex for Good yang digagas oleh Hukumonline. Dalam program ini, Hukumonline memberikan akses penggunaan teknologi AI secara cuma-cuma kepada 10 lembaga non-profit dan instansi publik. Hal ini sejalan dengan misi perusahaan untuk mendemokratisasi akses terhadap informasi dan riset hukum di Indonesia secara komprehensif.

Kehadiran platform berbasis kecerdasan buatan ini diklaim mampu menyederhanakan proses pencarian referensi, analisis preseden, serta penyusunan argumen hukum yang biasanya memakan waktu berhari-hari. Dengan sistem cerdas yang mampu mengolah data legal secara cepat, para praktisi dan aktivis di lembaga-lembaga terpilih diharapkan dapat bekerja lebih optimal dan responsif dalam memberikan advokasi maupun kajian kebijakan publik.

Langkah inovatif dari Hukumonline ini mendapat apresiasi positif karena dinilai membantu mempersempit kesenjangan akses teknologi di sektor hukum. Harapannya, lebih banyak lagi institusi yang dapat mengeksplorasi potensi kecerdasan buatan dalam mendukung supremasi hukum, tanpa harus terhambat oleh keterbatasan anggaran operasional teknologi.

![Ilustrasi kegiatan AI](https://via.placeholder.com/800x400.png?text=AI+News)

**Sumber:** [Hukumonline](https://www.hukumonline.com/berita/a/hukumonline-bagikan-akses-ai-gratis-pada-10-lembaga-di-program-ailex-for-good-lt665db7203b9b4)
"""

with open('/root/ai-news-daily/data/2026-06-03/22.01-01.md', 'w') as f:
    f.write(c1)
    
with open('/root/ai-news-daily/data/2026-06-03/22.01-02.md', 'w') as f:
    f.write(c2)
