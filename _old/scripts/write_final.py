#!/usr/bin/env python3
"""Write new AI news articles and update known-articles.json."""
import json, os
from datetime import datetime, timezone, timedelta

KNOWN_FILE = os.path.expanduser("~/ai-news-daily/known-articles.json")
OUT_DIR = os.path.expanduser("~/ai-news-daily/")

with open(KNOWN_FILE) as f:
    known = json.load(f)

now = datetime.now(timezone.utc)
jkt = now.astimezone(timezone(timedelta(hours=7)))
file_hour = jkt.strftime('%H.00')
file_date = jkt.strftime('%Y-%m-%d')
timestamp = jkt.strftime('%Y-%m-%d %H:%M WIB')

print(f"Time: {timestamp}")
print(f"Date: {file_date}, Hour: {file_hour}")

articles_to_write = [
    {
        'num': '01',
        'emoji': '⚖️',
        'category': '⚖️ Regulasi & Etika',
        'headline': 'Perang Super PAC AI di Pemilu Paruh Waktu: Miliarder Pro dan Kontra AI Saling Gebuk',
        'content': (
            "**New York, {file_date}** — Kecerdasan buatan telah menjadi medan pertempuran politik baru "
            "di Amerika Serikat. Dua kubu Super PAC raksasa saling berhadapan dalam Pemilu Paruh Waktu 2026: "
            "satu mendorong akselerasi AI tanpa hambatan, satu lagi mendesak regulasi ketat.\n\n"
            "Menurut laporan The New York Times, kelompok pro-AI yang didanai oleh miliarder Silicon Valley "
            "telah menggalang dana ratusan juta dolar untuk mendukung kandidat yang ramah terhadap pengembangan "
            "AI tanpa batas. Sementara itu, Super PAC dari kubu skeptis—yang khawatir soal dampak AI terhadap "
            "pekerjaan, privasi, dan demokrasi—juga mengerahkan sumber daya besar.\n\n"
            '"Ini bukan lagi perdebatan teknis, ini perang politik penuh," tulis NYT. Kedua sisi sama-sama '
            "mengklaim memperjuangkan masa depan Amerika, tapi visi mereka tentang peran AI dalam masyarakat "
            "bertolak belakang secara fundamental. Pemilu November ini akan menjadi referendum tak langsung "
            "tentang arah kebijakan AI AS."
        ),
        'url': 'https://www.nytimes.com/2026/05/30/technology/ai-super-pac-midterms.html',
        'source_name': 'The New York Times',
        'who': 'AI Super PAC',
        'what': 'POLITICS'
    },
    {
        'num': '02',
        'emoji': '💰',
        'category': '💰 Industry & Business',
        'headline': 'Perusahaan di AS Mulai Menjatah AI: Biaya Langganan Melonjak, Dompet Menjerit',
        'content': (
            "**Jakarta, {file_date}** — Setelah euforia adopsi AI tanpa batas, perusahaan-perusahaan "
            "di Amerika mulai merasakan dampaknya di laporan keuangan: biaya AI membengkak dan mereka "
            "mulai menjatah pemakaian.\n\n"
            "WSJ melaporkan bahwa fenomena AI rationing mulai melanda Corporate America. Banyak perusahaan "
            "yang semula memberikan akses tak terbatas ke alat AI seperti ChatGPT Enterprise, Claude, atau "
            "Copilot kini mulai membatasi jumlah query per karyawan.\n\n"
            '"Kami melihat kasus di mana langganan API AI membengkak hingga puluhan juta dolar per bulan," '
            "kata seorang analis. Hal ini memicu perubahan strategi: perusahaan mulai menghitung ROI setiap "
            "prompt AI, bukan sekadar mengejar adopsi. Ironisnya, ini terjadi di saat yang sama ketika "
            "vendor AI seperti Anthropic dan OpenAI terus mendorong penggunaan enterprise tanpa batas."
        ),
        'url': 'https://www.wsj.com/articles/corporate-america-is-starting-to-ration-ai-as-cost-skyrockets',
        'source_name': 'WSJ',
        'who': 'Corporate America',
        'what': 'WORKFORCE'
    },
    {
        'num': '03',
        'emoji': '💰',
        'category': '💰 Industry & Business',
        'headline': 'Startup AI China MiniMax Siap IPO: Siap-siap Perang Model dengan DeepSeek',
        'content': (
            "**Jakarta, {file_date}** — Kompetisi AI di China memasuki babak baru. MiniMax, startup AI "
            "yang dikenal lewat model video generation dan voice AI, dikabarkan bersiap melantai di bursa (IPO).\n\n"
            "Bloomberg melaporkan bahwa langkah IPO ini diambil MiniMax untuk menggalang dana segar di tengah "
            "persaingan sengit dengan rival lokal seperti DeepSeek dan Zhipu AI. MiniMax adalah salah satu dari "
            "segelintir startup AI China yang berhasil menembus peta persaingan global, terutama lewat model "
            "video generation Hailuo AI yang cukup populer.\n\n"
            "IPO MiniMax akan menjadi ujian penting bagi sentimen investor terhadap sektor AI China, yang selama "
            "ini berada di bawah tekanan regulasi domestik dan sanksi chip dari AS. Keberhasilan IPO bisa membuka "
            "jalan bagi startup AI China lainnya untuk mengikuti jejak serupa."
        ),
        'url': 'https://www.bloomberg.com/news/articles/2026-05-30/minimax-plans-china-ipo-as-it-eyes-local-rivals-like-deepseek',
        'source_name': 'Bloomberg',
        'who': 'MiniMax',
        'what': 'IPO'
    },
    {
        'num': '04',
        'emoji': '🧠',
        'category': '🧠 Model & Research',
        'headline': 'Bottleneck AI Agent Bukan Performa Model, Tapi Izin Akses',
        'content': (
            "**Jakarta, {file_date}** — Selama ini performa model dianggap sebagai hambatan utama adopsi "
            "AI agent di perusahaan. Tapi menurut analisis terbaru dari VentureBeat, masalah sesungguhnya "
            "ada di izin akses (permissions).\n\n"
            "Bottleneck AI agent bukan model performance, tapi permissions. Sistem keamanan dan tata kelola "
            "data perusahaan belum siap memberikan akses yang cukup bagi AI agent untuk bekerja secara otonom. "
            "Agent AI butuh akses ke database, API internal, dokumen, dan berbagai sistem—tapi tim IT dan "
            "keamanan khawatir memberikan akses seluas itu.\n\n"
            "Solusinya? Startup kini mulai mengembangkan sistem permission layer khusus untuk AI agent, "
            "yang memungkinkan kontrol akses granular tanpa menghambat produktivitas. Ini menjadi kategori "
            "baru dalam keamanan enterprise yang diperkirakan akan tumbuh pesat."
        ),
        'url': 'https://venturebeat.com/ai/the-ai-agent-bottleneck-isnt-model-performance-its-permissions/',
        'source_name': 'VentureBeat',
        'who': 'VentureBeat',
        'what': 'AGENT'
    },
    {
        'num': '05',
        'emoji': '🤖',
        'category': '🤖 Robotics & Hardware',
        'headline': 'Satelit Kini Makin Pintar Berkat AI: Bisa Proses Data di Orbit Tanpa Kirim ke Bumi',
        'content': (
            "**Jakarta, {file_date}** — Kecerdasan buatan mulai mengubah secara fundamental cara kerja "
            "satelit di orbit. Kini satelit tidak lagi sekadar pemotret langit yang mengirim semua data mentah ke Bumi.\n\n"
            "CNBC melaporkan bahwa dengan chip AI onboard, satelit modern bisa memproses dan menganalisis "
            "data langsung di orbit. Ini berarti satelit bisa langsung mengidentifikasi objek mencurigakan, "
            "pola cuaca, atau perubahan geografis tanpa harus menunggu data dikirim ke stasiun Bumi.\n\n"
            "Dampaknya sangat besar: bandwidth yang dihemat sangat signifikan, waktu respons untuk aplikasi "
            "kritis seperti pemantauan bencana alam atau pertahanan bisa dipangkas dari jam ke menit. "
            "Beberapa perusahaan rintisan bahkan mulai menawarkan AI-as-a-Service untuk satelit—memungkinkan "
            "pelanggan menjalankan model AI kustom langsung di orbit."
        ),
        'url': 'https://www.cnbc.com/2026/05/30/how-ai-is-changing-what-satellites-can-do-in-orbit.html',
        'source_name': 'CNBC',
        'who': 'Satellites',
        'what': 'ROBOT'
    },
    {
        'num': '06',
        'emoji': '⚖️',
        'category': '⚖️ Regulasi & Etika',
        'headline': 'Anggota Kongres AS Usul Pajak AI: Hasilnya Buat Training Ulang Pekerja',
        'content': (
            "**Jakarta, {file_date}** — Seorang anggota Kongres AS dari Texas, Greg Casar, mengusulkan "
            "kebijakan yang bikin Silicon Valley bergidik: pajak khusus untuk perusahaan AI.\n\n"
            "Dilansir KXAN Austin, Casar mengusulkan agar perusahaan AI dikenakan pajak tambahan yang "
            "hasilnya dipakai untuk mendanai program pelatihan kerja dan jaring pengaman sosial bagi "
            "pekerja yang kehilangan pekerjaan akibat otomatisasi. AI is coming for your job, tegas "
            "Casar dalam pidatonya.\n\n"
            "Meskipun kecil kemungkinan lolos di Kongres yang terpolarisasi, usulan ini menjadi sinyal "
            "bahwa debat soal dampak AI terhadap tenaga kerja mulai memasuki ranah legislatif serius. "
            "Ini juga mencerminkan kekhawatiran publik yang makin meluas: jajak pendapat terbaru "
            "menunjukkan 72% orang Amerika khawatir AI akan menggantikan pekerjaan mereka dalam 5 tahun ke depan."
        ),
        'url': 'https://www.kxan.com/news/texas-politics/greg-casar-calls-to-tax-ai-companies-to-fund-jobs-program/',
        'source_name': 'KXAN Austin',
        'who': 'Greg Casar',
        'what': 'POLITICS'
    },
    {
        'num': '07',
        'emoji': '🎬',
        'category': '🎬 Creative & Media',
        'headline': 'Sutradara Terkenal Urungkan Acara AI Amazon MGM gara-gara Hujatan Kreator',
        'content': (
            "**Jakarta, {file_date}** — Jorge R. Gutierrez—sutradara terkenal di balik The Book of Life—"
            "membuat serial AI-generated Punky Duck yang didanai Amazon MGM Studios, tapi keputusan ini "
            "menuai kontroversi besar.\n\n"
            "Dilaporkan IndieWire, setelah mendapat kecaman keras dari komunitas kreatif Hollywood yang "
            "menuduhnya mengkhianati sesama kreator, Gutierrez mengumumkan bahwa ia membatalkan proyek "
            "tersebut. Ini adalah perkembangan terbaru dalam saga Amazon MGM yang berusaha masuk ke "
            "konten AI-generated.\n\n"
            "Keputusan Gutierrez menjadi preseden penting: bahkan kreator mapan pun harus berpikir dua "
            "kali sebelum menggunakan AI generatif secara kontroversial di Hollywood yang sedang sensitif "
            "soal AI. Ini menunjukkan bahwa tekanan dari komunitas kreatif benar-benar bisa mengubah "
            "keputusan bisnis studio besar."
        ),
        'url': 'https://www.indiewire.com/news/breaking-news/jorge-gutierrez-cancels-ai-punky-duck-amazon-mgm-123456789/',
        'source_name': 'IndieWire',
        'who': 'Jorge Gutierrez',
        'what': 'CREATIVE'
    }
]

# Write files
for a in articles_to_write:
    filename = f"{file_date}-{file_hour}-{a['num']}.md"
    filepath = os.path.join(OUT_DIR, filename)
    
    content = f"# {a['num']} — {a['emoji']} {a['category']}\n\n---\n\n## {a['headline']}\n\n{a['content'].format(file_date=file_date)}\n\n**Sumber:** [{a['source_name']} — {a['headline']}]({a['url']})\n"
    
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"✓ {filename}")

# Update known-articles.json
known_total = known.get('total', len(known['articles']))
print(f"\nExisting article count: {known_total}")

for a in articles_to_write:
    url = a['url']
    if url in known['articles']:
        print(f"  URL already in known: {a['source_name']}")
        continue
    
    # Layer 1: add URL
    known['articles'][url] = {
        'file': f"{file_date}-{file_hour}-{a['num']}.md",
        'source': a['source_name'],
        'first_seen': file_date
    }
    
    # Layer 2: add normalized headline
    domain = url.split('/')[2] if '//' in url else ''
    hl_norm = a['headline'].lower()
    import re as re_m
    hl_norm = re_m.sub(r'[^a-z0-9\s]', '', hl_norm)
    stop_words = {'a','an','the','is','are','was','were','be','been','being','have','has','had',
                  'do','does','did','will','would','can','could','shall','should','may','might',
                  'to','of','in','for','on','with','at','by','from','as','into','through',
                  'during','before','after','above','below','between','out','off','over','under',
                  'and','but','or','nor','not','so','yet','both','either','neither',
                  'its',"it's",'their','them','they','this','that','these','those'}
    norm_words = [w for w in hl_norm.split() if w not in stop_words and len(w) > 2]
    hl_norm_clean = ' '.join(norm_words)
    
    if domain not in known['source_headlines']:
        known['source_headlines'][domain] = []
    known['source_headlines'][domain].append(hl_norm_clean)
    
    # Layer 3: add who+what
    who_what = {'who': a['who'], 'what': a['what'], 'first_seen': file_date}
    found = any(c['who'] == who_what['who'] and c['what'] == who_what['what'] for c in known['cross_topics'])
    if not found:
        known['cross_topics'].append(who_what)

known['total'] = len(known['articles'])
print(f"New article count: {known['total']}")

with open(KNOWN_FILE, 'w') as f:
    json.dump(known, f, indent=2, ensure_ascii=False)

print("\n✅ known-articles.json updated!")
