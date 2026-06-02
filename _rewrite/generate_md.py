#!/usr/bin/env python3
"""Generate missing .md article files for 2026-06-02 from md_batch.json"""
import json, os, sys

BASE = "/root/ai-news-daily"

with open(f"{BASE}/_rewrite/md_batch.json") as f:
    articles = json.load(f)

# Categories mapping based on content analysis
CATEGORIES = {
    # 1 - DuckDuckGo, No AI strategy
    "12.00-01.md": "Industry & Business",
    # 2 - Anthropic IPO
    "00.06-01.md": "Industry & Business",
    # 3 - WindBorne weather AI
    "00.06-02.md": "Model & Research",
    # 4 - Nvidia RTX Spark
    "01.03-01.md": "Robotics & Hardware",
    # 5 - Intel Crescent Island
    "01.03-02.md": "Robotics & Hardware",
    # 6 - Florida sues OpenAI
    "03.00-01.md": "Regulasi & Etika",
    # 7 - Robot startup Airbnb
    "03.00-02.md": "Robotics & Hardware",
    # 8 - SpaceX IPO water
    "05.03-01.md": "Industry & Business",
    # 9 - Meta chatbot hacked
    "05.03-02.md": "Regulasi & Etika",
    # 10 - GM AI design
    "05.03-03.md": "Model & Research",
    # 11 - Alphabet $80B
    "06.07-1.md": "Industry & Business",
    # 12 - Sanders AI fund
    "06.07-2.md": "Regulasi & Etika",
    # 13 - Nvidia CPU AI Agent
    "07.06-01.md": "Robotics & Hardware",
    # 14 - GitHub Copilot pricing
    "09.01-01.md": "Industry & Business",
    # 15 - AI nude images
    "09.01-02.md": "Regulasi & Etika",
    # 16 - HPE record
    "11.00-01.md": "Industry & Business",
    # 17 - Microsoft Surface Ultra
    "11.00-02.md": "Robotics & Hardware",
    # 18 - Microsoft Build AI
    "12.00-02.md": "Model & Research",
    # 19 - Strava API
    "12.00-03.md": "Industry & Business",
    # 20 - NVIDIA Jetson agentic
    "13.00-01.md": "Robotics & Hardware",
    # 21 - GM simulation (duplicate URL, different angle)
    "14.06-01.md": "Model & Research",
    # 22 - Harvard AI study
    "14.06-02.md": "Model & Research",
    # 23 - Trump regulation
    "15.13-01.md": "Regulasi & Etika",
    # 24 - Nvidia DLSS 4.5
    "15.13-02.md": "Creative & Media",
    # 25 - ByteDance loses AI lead
    "16.00-01.md": "Industry & Business",
    # 26 - Tencent WeChat AI
    "16.00-02.md": "Industry & Business",
    # 27 - BBC AI strategy
    "17.06-01.md": "Industry & Business",
    # 28 - Tripo AI $200M
    "18.09-01.md": "Model & Research",
    # 29 - BadBone backdoor
    "18.09-03.md": "Regulasi & Etika",
    # 30 - Walmart limits AI
    "19.00-01.md": "Industry & Business",
    # 31 - ZeroDrift $10M
    "20.07-02.md": "Regulasi & Etika",
    # 32 - Impulse $500M
    "20.07-03.md": "Industry & Business",
    # 33 - Gemini Spark
    "20.07-01.md": "Model & Research",
    # 34 - MiniMax M3
    "21.06-01.md": "Model & Research",
    # 35 - Claude browser hijack
    "21.06-02.md": "Regulasi & Etika",
    # 36 - Claude Mythos infrastructure
    "22.05-01.md": "Industry & Business",
    # 37 - Claude Mythos patching
    "22.05-03.md": "Regulasi & Etika",
}

# Title generation from thumb_lines
TITLES = {
    "12.00-01.md": "DuckDuckGo Raup Banyak Pengguna Baru — Strategi No AI Justru Makin Laris",
    "00.06-01.md": "Anthropic Resmi Ajukan IPO ke Publik — Target Valuasi Tembus Satu Triliun Dolar",
    "00.06-02.md": "WindBorne Prediksi Cuaca Lebih Akurat dari Pemerintah — Pakai 400 Balon Udara untuk Data Real-Time",
    "01.03-01.md": "Nvidia Resmi Bikin Chip PC — RTX Spark: Arm + GPU Desktop Siap Lawan Apple & Qualcomm",
    "01.03-02.md": "Intel Balas Dendam ke Nvidia — Crescent Island GPU: Lebih Murah, Pakai LPDDR5, Air-Cooled!",
    "03.00-01.md": "Florida Gugat OpenAI & Sam Altman — ChatGPT Dituding Bantu Rencana Pembunuhan",
    "03.00-02.md": "Startup Robot Merusak Airbnb — Uji Coba Robot Berakhir Gugatan, Rusak Rumah Harga 2 Ribu!",
    "05.03-01.md": "IPO SpaceX Peringatkan Krisis Air — Data Center AI Butuh Banyak Air, Biaya Lingkungan Mulai Terasa",
    "05.03-02.md": "Chatbot Meta Bisa Dibobol Hacker — Akun Instagram Selebriti Raib, Celah Keamanan AI Berbahaya",
    "05.03-03.md": "AI Ubah Proses Desain GM — Dari 15 Jam Jadi 1 Menit, Simulasi Tabrakan Lebih Cepat",
    "06.07-1.md": "Alphabet Siap Kumpulkan $80 Miliar — Dana Terbesar Buat AI Infrastructure dari Jual Saham",
    "06.07-2.md": "Sanders Usulkan Dana Kekayaan Berdaulat AI — Pajak AI Buat Program Sosial",
    "07.06-01.md": "Nvidia Gas Pasar CPU PC — RTX Spark Siap Jadi Otak AI Agent, Pasar $200 Miliar Mulai Dicaplok",
    "09.01-01.md": "GitHub Copilot Bikin Kaget Developer — Sistem Harga Baru Bikin Tagihan Membengkak, Jatah Bulanan Habis Dalam Sehari",
    "09.01-02.md": "Otoritas di Seluruh Dunia Kewalahan Lawan AI — Alat Hasilkan Gambar Vulgar Tanpa Izin, Regulasi Berjalan Lambat",
    "11.00-01.md": "HPE Cetak Rekor Berkat AI — Pendapatan Tembus 10,7 Miliar, Saham Melonjak 90 Persen Tahun Ini",
    "11.00-02.md": "Microsoft Surface Laptop Ultra — PC AI Pertama dengan Chip Nvidia Arm, RAM 128GB Siap Lawan MacBook Pro",
    "12.00-02.md": "Microsoft Siap Umumkan Model AI Baru — Konferensi Build Pekan Ini, Copilot Super App Juga Dikabarkan Hadir",
    "12.00-03.md": "Strava Batasi Akses API — Bayar USD 11,99 per Bulan, Akibat Serbuan Aplikasi AI Tanpa Kode",
    "13.00-01.md": "Agentic AI Kini di Perangkat Fisik — NVIDIA Rilis JetPack 7.2 dan NemoClaw, Robot dan Pabrik Makin Otonom",
    "14.06-01.md": "AI Ubah Waktu Simulasi GM — Dari 15 Jam Jadi 1 Menit, Ribuan Skenario Bisa Diparalelkan",
    "14.06-02.md": "Studi Harvard: Cara Orang Pakai AI — Tugas Rutin Dominan, Strategis Masih Minim, Tingkat Stres Pekerja Meningkat",
    "15.13-01.md": "Trump Targetkan Regulasi AI — Negara Bagian dengan Aturan Baru, Illinois dan California Lawan",
    "15.13-02.md": "Nvidia Rilis DLSS 4.5 Baru — Bisa untuk Semua GPU RTX, Gaming Pakai AI Lebih Canggih",
    "16.00-01.md": "ByteDance Kehilangan Pimpinan Riset AI — Gu Quanquan Tinggalkan Seed Models, Monetisasi AI Makin Tertekan",
    "16.00-02.md": "Saham Tencent Melonjak 10 Persen — AI Agent Segera Hadir di WeChat, 1,4 Miliar Pengguna Tersambung",
    "17.06-01.md": "Strategi AI Bikin Bingung — Perusahaan Terjebak Tren Tanpa Rencana Jelas, Karyawan Frustrasi",
    "18.09-01.md": "Tripo AI Kumpulkan Hampir USD 200 Juta — Kembangkan AI 3D dan World Model, Bisa Ciptakan Dunia Virtual",
    "18.09-03.md": "Peneliti Temukan Backdoor AI Baru — BadBone Bisa Bobol Tanpa Terdeteksi, Enam Tools Keamanan Gagal Total",
    "19.00-01.md": "Walmart Batasi Pemakaian AI — Token Karyawan Mulai Dibatasi, Biaya AI Membengkak di Luar Kendali",
    "20.07-02.md": "ZeroDrift Kumpulkan $10 Juta — Lindungi AI dari Dirinya Sendiri, Solusi Kepatuhan AI Generatif",
    "20.07-03.md": "Impulse Kumpulkan $500 Juta — Pilih Rekrut Manusia Bukan AI, Pendekatan Human-Centric di Aerospace",
    "20.07-01.md": "Gemini Spark AI Agent — Bisa Kerja 24/7 Tanpa Henti, Paling Mengesankan dan Menyeramkan",
    "21.06-01.md": "MiniMax M3 Kalahkan GPT-5.5 dan Gemini 3.1 Pro — Hanya 10 Persen Biayanya!",
    "21.06-02.md": "Browser AI Claude Bisa Dibajak — 31,5 Persen Sekali Coba, Anthropic Buka Data Keamanan",
    "22.05-01.md": "Anthropic Perluas Claude Mythos — Infrastruktur Kritis 15 Negara, NATO dan Samsung Ikut Serta",
    "22.05-03.md": "Claude Mythos Buka Fakta — Proses Patching Terlalu Lambat, Eksploitasi Cuma 9 Jam",
}

# Captions (3-5 paragraphs each, in Indonesian)
CAPTIONS = {
    "12.00-01.md": (
        "DuckDuckGo baru saja meluncurkan ekstensi browser khusus untuk Chrome dan Firefox, memperkuat posisinya sebagai mesin pencari yang mengutamakan privasi tanpa kecanggihan AI. Langkah ini justru berhasil menarik banyak pengguna baru di tengah hiruk-pikuk persaingan AI.\n\n"
        "Dalam beberapa bulan terakhir, DuckDuckGo mencatat lonjakan traffic yang signifikan — membuktikan bahwa strategi 'no AI' bisa menjadi nilai jual yang unik di pasar yang semakin jenuh dengan fitur-fitur kecerdasan buatan.\n\n"
        "Dengan pendekatan yang fokus pada privasi dan pengalaman pencarian yang bersih, DuckDuckGo berhasil menciptakan ceruk pasar tersendiri yang terbukti diminati oleh segmen pengguna yang mulai lelah dengan dominasi AI di setiap layanan digital.\n\n"
        "Ini menjadi bukti bahwa tidak semua pengguna menginginkan AI dalam setiap aspek pencarian mereka — dan terkadang, kesederhanaan justru menjadi daya tarik terbesar."
    ),
    "00.06-01.md": (
        "Anthropic, startup AI di balik model Claude, secara resmi mengajukan IPO ke publik dengan target valuasi yang dikabarkan tembus satu triliun dolar. Ini menjadi IPO startup AI yang paling dinanti sepanjang masa.\n\n"
        "Langkah ini menandai babak baru dalam industri AI, di mana pemain utama mulai beralih dari pendanaan venture capital ke pasar publik. Kesuksesan IPO Anthropic bisa menjadi barometer bagi startup AI lainnya yang juga bersiap melantai di bursa.\n\n"
        "Para analis memprediksi bahwa IPO ini akan menjadi salah satu yang terbesar dalam sejarah teknologi, mencerminkan kepercayaan pasar terhadap potensi jangka panjang AI.\n\n"
        "Anthropic sendiri dikenal dengan pendekatan safety-first dalam pengembangan AI, yang menjadi nilai jual utama di tengah kekhawatiran publik tentang risiko kecerdasan buatan."
    ),
    "00.06-02.md": (
        "WindBorne, sebuah startup AI cuaca, berhasil membuat prediksi yang lebih akurat dibandingkan badan meteorologi pemerintah. Dengan menggunakan 400 balon udara yang menyebar di berbagai titik, mereka mengumpulkan data real-time dari atmosfer.\n\n"
        "Teknologi AI WeatherMesh 6 milik WindBorne mampu mengalahkan akurasi prediksi badan cuaca Eropa yang selama ini menjadi standar global. Pendekatan berbasis data real-time ini memberikan keunggulan signifikan.\n\n"
        "Balon-balon udara tersebut mampu menjangkau ketinggian dan area yang sulit dijangkau oleh metode konvensional, memberikan sampel data atmosfer yang lebih kaya dan lebih sering diperbarui.\n\n"
        "Keberhasilan ini membuka peluang baru bagi startup AI untuk bersaing dengan institusi pemerintah yang sudah mapan, sekaligus menunjukkan potensi AI dalam menyelesaikan masalah kompleks seperti prediksi cuaca."
    ),
    "01.03-01.md": (
        "Nvidia resmi memasuki bisnis chip PC dengan meluncurkan prosesor RTX Spark, sebuah chip berbasis arsitektur Arm yang dipadukan dengan GPU desktop. Langkah ini menjadi ancaman serius bagi Apple dan Qualcomm.\n\n"
        "RTX Spark dirancang untuk memberikan performa tinggi dengan efisiensi daya yang optimal, menggabungkan kemampuan CPU dan GPU dalam satu paket yang kompak. Ini adalah pertama kalinya Nvidia benar-benar bersaing di pasar CPU PC.\n\n"
        "Dengan pengalaman Nvidia di dunia GPU dan AI, RTX Spark diprediksi akan menjadi game-changer khususnya untuk aplikasi-aplikasi yang membutuhkan komputasi paralel dan kemampuan AI di perangkat personal.\n\n"
        "Langkah ini juga memperkuat posisi Arm di pasar PC desktop, yang selama ini didominasi oleh arsitektur x86 dari Intel dan AMD."
    ),
    "01.03-02.md": (
        "Intel tidak tinggal diam menghadapi dominasi Nvidia. Mereka mengumumkan chip AI terbaru bernama Crescent Island GPU yang diklaim lebih murah dan lebih dingin dibandingkan kompetitor.\n\n"
        "Dengan menggunakan memori LPDDR5 dan sistem pendingin udara (air-cooled), Intel menyasar segmen pasar yang membutuhkan solusi AI dengan biaya operasional lebih rendah. Ini adalah strategi differensiasi yang cerdas.\n\n"
        "Crescent Island GPU dirancang khusus untuk inference AI dan workload machine learning, bukan untuk gaming. Pendekatan fokus ini memungkinkan Intel mengoptimalkan biaya dan efisiensi.\n\n"
        "Intel berharap chip ini bisa merebut pangsa pasar dari Nvidia, terutama di segmen enterprise dan data center yang sensitif terhadap biaya dan konsumsi daya."
    ),
    "03.00-01.md": (
        "Florida secara resmi menggugat OpenAI dan CEO Sam Altman setelah beberapa kasus pembunuhan dikaitkan dengan penggunaan ChatGPT. Gugatan ini menjadi yang pertama dalam sejarah AS.\n\n"
        "Pemerintah negara bagian Florida menuduh bahwa ChatGPT telah digunakan untuk membantu merencanakan aksi kriminal, termasuk pembunuhan. Kasus ini memicu perdebatan sengit tentang tanggung jawab platform AI.\n\n"
        "Ini adalah preseden hukum yang sangat signifikan — untuk pertama kalinya, perusahaan AI digugat atas tindakan penggunanya dengan tuduhan kelalaian dalam keamanan produk.\n\n"
        "Kasus ini diprediksi akan menjadi ujian besar bagi industri AI, dan bisa mempengaruhi bagaimana perusahaan AI mengimplementasikan safety measures ke depannya."
    ),
    "03.00-02.md": (
        "Sebuah startup yang mengembangkan robot untuk tugas-tugas rumah tangga justru berurusan dengan hukum setelah robot yang mereka uji coba merusak properti Airbnb. Kerusakan dilaporkan mencapai ribuan dolar.\n\n"
        "Insiden ini terjadi saat robot sedang diuji di lingkungan nyata — sebuah properti sewaan yang digunakan sebagai laboratorium uji coba. Robot tersebut dilaporkan menabrak perabotan dan merusak dinding.\n\n"
        "Pemilik properti menggugat startup tersebut atas kerusakan yang terjadi, memicu pertanyaan tentang asuransi dan tanggung jawab hukum dalam pengujian robot di lingkungan publik.\n\n"
        "Kasus ini menjadi pelajaran berharga bagi industri robotika: uji coba di lingkungan nyata tetap membutuhkan pengawasan manusia dan perlindungan asuransi yang memadai."
    ),
    "05.03-01.md": (
        "IPO SpaceX yang akan datang mencantumkan akses air sebagai faktor risiko dalam prospektusnya. Data center AI yang semakin membengkak membutuhkan pasokan air dalam jumlah besar untuk sistem pendingin.\n\n"
        "Fakta bahwa perusahaan milik Elon Musk ini secara eksplisit menyebut krisis air dalam dokumen IPO menunjukkan betapa seriusnya dampak lingkungan dari ledakan AI.\n\n"
        "Data center AI modern mengonsumsi air dalam jumlah masif — diperkirakan satu data center besar bisa menggunakan jutaan galon air per hari untuk mendinginkan server-server AI yang bekerja non-stop.\n\n"
        "Ini menjadi sorotan baru dalam perdebatan tentang keberlanjutan AI: selain konsumsi energi yang besar, dampak terhadap sumber daya air juga mulai menjadi perhatian investor dan regulator."
    ),
    "05.03-02.md": (
        "Sebuah celah keamanan serius ditemukan pada chatbot AI Meta yang memungkinkan hacker mengambil alih akun Instagram milik selebriti dan tokoh terkenal. Kerentanan ini menimbulkan kekhawatiran besar.\n\n"
        "Para hacker berhasil mengeksploitasi fitur support chatbot Meta untuk mendapatkan akses ke akun-akun ternama, menjadikannya sebagai vektor serangan yang tidak terduga sebelumnya.\n\n"
        "Meta telah merilis perbaikan darurat, namun insiden ini menyoroti risiko keamanan yang melekat pada sistem AI yang terintegrasi dengan layanan konsumen.\n\n"
        "Para ahli keamanan memperingatkan bahwa semakin banyak perusahaan mengintegrasikan AI ke dalam layanan pelanggan, semakin besar pula permukaan serangan yang harus diamankan."
    ),
    "05.03-03.md": (
        "General Motors (GM) mengungkapkan bahwa AI dan machine learning telah mempercepat proses desain mereka secara drastis — dari 15 jam menjadi hanya 1 menit untuk simulasi tabrakan tertentu.\n\n"
        "Teknologi ini memungkinkan para insinyur GM untuk menjalankan ribuan skenario simulasi dalam waktu yang sangat singkat, sesuatu yang sebelumnya memakan waktu berminggu-minggu.\n\n"
        "Hasilnya, proses pengembangan mobil baru menjadi jauh lebih efisien, memungkinkan GM untuk merespons perubahan pasar lebih cepat dan menguji lebih banyak variasi desain.\n\n"
        "GM mengklaim bahwa penerapan AI dalam proses desain ini tidak hanya menghemat waktu tetapi juga meningkatkan kualitas dan keamanan kendaraan yang dihasilkan."
    ),
    "06.07-1.md": (
        "Alphabet, perusahaan induk Google, berencana mengumpulkan dana sebesar $80 miliar melalui penjualan saham untuk membiayai pembangunan infrastruktur AI. Ini adalah penggalangan dana terbesar yang pernah dilakukan.\n\n"
        "Dana tersebut akan digunakan untuk membangun lebih banyak data center, membeli chip AI, dan memperkuat kapasitas komputasi cloud Google untuk mendukung pengembangan AI generatif.\n\n"
        "Langkah ini menunjukkan betapa besarnya investasi yang dibutuhkan untuk bersaing di era AI — bahkan bagi perusahaan sekelas Alphabet sekalipun.\n\n"
        "Pengumuman ini juga menjadi sinyal bahwa kompetisi infrastruktur AI semakin memanas, dengan para raksasa teknologi berlomba-lomba mengamankan sumber daya komputasi."
    ),
    "06.07-2.md": (
        "Senator Bernie Sanders mengusulkan undang-undang baru yang akan menciptakan AI Sovereign Wealth Fund — dana kekayaan berdaulat yang didanai dari pajak perusahaan AI. Ini adalah pendekatan progresif terhadap regulasi AI.\n\n"
        "Konsepnya sederhana: perusahaan AI akan dikenakan pajak khusus, dan hasilnya akan digunakan untuk program-program sosial seperti pendidikan ulang tenaga kerja yang terdampak otomatisasi.\n\n"
        "Usulan ini memicu perdebatan sengit di kalangan pembuat kebijakan. Pendukungnya mengatakan ini adalah cara yang adil untuk mendistribusikan keuntungan dari AI ke masyarakat luas.\n\n"
        "Sementara itu, kritikus khawatir pajak tambahan akan menghambat inovasi dan membuat perusahaan AI AS kurang kompetitif secara global."
    ),
    "07.06-01.md": (
        "Nvidia semakin agresif mengejar pasar CPU PC senilai $200 miliar dengan chip RTX Spark yang dirancang khusus untuk AI Agent. Microsoft, Dell, dan HP sudah dikonfirmasi sebagai partner awal.\n\n"
        "RTX Spark tidak hanya dirancang sebagai CPU biasa, tetapi dioptimalkan untuk menjalankan AI agent — asisten cerdas yang bisa bekerja secara otonom di perangkat pengguna.\n\n"
        "Kemitraan dengan tiga raksasa PC dunia ini memberi Nvidia akses langsung ke pasar enterprise dan konsumen yang sangat luas, mempercepat adopsi chip Arm untuk AI.\n\n"
        "Ini adalah langkah berani yang bisa mengguncang dominasi Intel dan AMD di pasar CPU, sekaligus memperkuat posisi Nvidia sebagai pemimpin infrastruktur AI."
    ),
    "09.01-01.md": (
        "GitHub Copilot baru saja beralih ke sistem harga berbasis pemakaian (usage-based pricing) dan para developer langsung merasakan dampaknya — tagihan membengkak drastis.\n\n"
        "Banyak developer melaporkan bahwa jatah bulanan mereka habis dalam sehari, terutama bagi yang sering menggunakan Copilot untuk coding intensif. Sistem baru ini menghitung setiap permintaan secara terpisah.\n\n"
        "Keputusan ini menuai kritik tajam dari komunitas developer yang merasa bahwa Copilot menjadi terlalu mahal untuk penggunaan sehari-hari, terutama untuk proyek-proyek open-source.\n\n"
        "Microsoft dan GitHub berargumen bahwa model harga baru ini lebih adil — pengguna hanya membayar sesuai pemakaian. Namun banyak yang mempertanyakan apakah ini benar-benar soal keadilan atau sekadar strategi monetisasi."
    ),
    "09.01-02.md": (
        "Otoritas di berbagai negara kewalahan menghadapi gelombang alat AI yang bisa menghasilkan gambar vulgar tanpa izin. Teknologi ini semakin mudah diakses dan sulit diberantas.\n\n"
        "Meskipun beberapa negara sudah memiliki undang-undang yang mengatur konten AI, implementasi di lapangan masih sangat lambat. Alat-alat ini terus bermunculan dengan versi yang lebih canggih.\n\n"
        "Para korban — terutama perempuan — harus berjuang melawan penyebaran gambar-gambar tersebut sementara proses hukum berjalan sangat lambat. Banyak yang merasa sistem hukum belum siap menghadapi tantangan ini.\n\n"
        "Para ahli mendesak pemerintah untuk segera memperbarui undang-undang dan memberikan kewenangan lebih besar kepada platform untuk memblokir konten semacam ini secara proaktif."
    ),
    "11.00-01.md": (
        "HPE (Hewlett Packard Enterprise) mencatat rekor pendapatan berkat bisnis server AI mereka, dengan pendapatan menembus angka $10,7 miliar. Saham perusahaan melonjak 90 persen tahun ini.\n\n"
        "Permintaan server AI yang terus meroket menjadi motor utama pertumbuhan HPE, seiring dengan semakin banyaknya perusahaan yang membangun infrastruktur AI mereka sendiri.\n\n"
        "Rekor ini menunjukkan bahwa ledakan AI tidak hanya menguntungkan perusahaan software, tetapi juga perusahaan hardware yang memasok infrastruktur fisik.\n\n"
        "HPE diprediksi akan terus tumbuh seiring dengan meningkatnya kebutuhan data center AI di seluruh dunia, terutama dengan tren AI on-premise yang kembali populer."
    ),
    "11.00-02.md": (
        "Microsoft mengumumkan Surface Laptop Ultra, PC AI pertama yang menggunakan chip Nvidia Arm — RTX Spark. Dengan RAM hingga 128GB, laptop ini siap menjadi lawan sepadan MacBook Pro.\n\n"
        "Surface Laptop Ultra dirancang khusus untuk menjalankan AI workload secara lokal, memanfaatkan GPU Nvidia terintegrasi untuk akselerasi AI yang optimal.\n\n"
        "Kombinasi chip Nvidia Arm dan RAM besar membuat perangkat ini ideal untuk developer AI, content creator, dan profesional yang membutuhkan komputasi berat di perangkat mobile.\n\n"
        "Ini adalah langkah strategis Microsoft untuk memperkuat ekosistem Windows di era AI, bersaing langsung dengan Apple Silicon yang selama ini unggul dalam performa per watt."
    ),
    "12.00-02.md": (
        "Microsoft dikabarkan akan mengumumkan model AI baru dan Copilot Super App dalam konferensi Build pekan ini. Spekulasi semakin kuat menjelang acara tahunan tersebut.\n\n"
        "Model AI baru ini diyakini akan menjadi dasar bagi berbagai produk Microsoft ke depannya, sementara Copilot Super App dikabarkan akan mengintegrasikan berbagai layanan AI dalam satu platform.\n\n"
        "Konferensi Build tahun ini diprediksi menjadi salah satu yang paling penting bagi Microsoft, dengan AI sebagai tema sentral di hampir semua pengumuman.\n\n"
        "Para pengamat industri menantikan apakah Microsoft bisa mempertahankan momentumnya di era AI setelah keberhasilan awal Copilot dan kemitraan dengan OpenAI."
    ),
    "12.00-03.md": (
        "Strava, platform kebugaran populer, membatasi akses API mereka dengan memberlakukan biaya berlangganan $11,99 per bulan. Langkah ini dipicu oleh serbuan aplikasi AI tanpa kode yang mulai membebani infrastruktur.\n\n"
        "Dengan semakin mudahnya membuat aplikasi menggunakan AI tanpa coding, banyak developer yang membuat aplikasi Strava pihak ketiga secara massal, membebani server dan meningkatkan biaya operasional.\n\n"
        "Kebijakan baru ini diharapkan bisa menyaring developer yang serius dari yang hanya sekadar mencoba-coba, sekaligus menjadi sumber pendapatan tambahan bagi Strava.\n\n"
        "Namun, langkah ini juga dikritik oleh komunitas developer kecil yang merasa bahwa biaya berlangganan terlalu mahal untuk proyek-proyek hobi atau non-komersial."
    ),
    "13.00-01.md": (
        "NVIDIA resmi merilis JetPack 7.2 dan NemoClaw, membawa kemampuan Agentic AI ke perangkat fisik. Robot dan pabrik kini bisa beroperasi dengan tingkat otonomi yang lebih tinggi.\n\n"
        "Dengan teknologi ini, perangkat edge computing seperti robot bisa membuat keputusan secara real-time tanpa harus terhubung ke cloud, mengurangi latency dan meningkatkan keandalan.\n\n"
        "NemoClaw, framework baru NVIDIA untuk robotika, memungkinkan pengembangan AI agent yang bisa beradaptasi dengan lingkungan fisik secara dinamis — langkah besar menuju robot serba guna.\n\n"
        "Ini adalah perkembangan signifikan untuk industri manufaktur, logistik, dan sektor-sektor lain yang mengandalkan otomatisasi fisik."
    ),
    "14.06-01.md": (
        "GM kembali menunjukkan keajaiban AI dalam proses desain mereka: waktu simulasi yang dulunya 15 jam kini bisa diselesaikan dalam 1 menit. Lebih impressif lagi, ribuan skenario bisa diparalelkan secara bersamaan.\n\n"
        "Kemampuan ini membuka pintu untuk pengujian yang jauh lebih komprehensif — tidak hanya puluhan skenario, tetapi ribuan variasi kondisi bisa diuji dalam waktu yang sama.\n\n"
        "Dengan pendekatan ini, GM bisa mengidentifikasi potensi masalah desain lebih awal, menghemat biaya pengembangan yang mahal di tahap akhir.\n\n"
        "AI tidak hanya mempercepat proses, tetapi juga meningkatkan kualitas akhir produk dengan memungkinkan optimasi yang lebih mendalam di setiap aspek desain."
    ),
    "14.06-02.md": (
        "Sebuah studi dari Harvard mengungkapkan realitas penggunaan AI di tahun 2026: mayoritas pekerja masih menggunakannya untuk tugas-tugas rutin, sementara penggunaan strategis masih sangat minim.\n\n"
        "Yang mengejutkan, tingkat stres pekerja justru meningkat meskipun AI seharusnya meringankan beban kerja. Para peneliti menemukan bahwa kekhawatiran akan digantikan AI menjadi faktor utama.\n\n"
        "Studi ini juga menemukan kesenjangan signifikan antara generasi muda yang lebih adaptif dengan AI dibandingkan pekerja senior, menciptakan dinamika baru di tempat kerja.\n\n"
        "Harvard merekomendasikan perusahaan untuk lebih fokus pada pelatihan dan pendampingan, bukan hanya sekadar menyediakan alat AI, agar manfaatnya bisa dirasakan secara optimal."
    ),
    "15.13-01.md": (
        "Pemerintahan Trump menargetkan regulasi AI dengan mendorong negara-negara bagian untuk membuat aturan sendiri. Illinois dan California menjadi yang paling vokal menentang pendekatan ini.\n\n"
        "Alih-alih regulasi federal yang seragam, pendekatan Trump lebih memberikan kebebasan kepada negara bagian — namun dikritik karena bisa menciptakan ketidakpastian hukum bagi perusahaan AI.\n\n"
        "Illinois dan California mengkhawatirkan bahwa tanpa standar nasional yang kuat, akan muncul celah regulasi yang bisa dieksploitasi oleh perusahaan AI.\n\n"
        "Perdebatan ini mencerminkan tensi yang lebih luas antara pendekatan pro-inovasi dan pro-perlindungan konsumen dalam kebijakan AI di Amerika Serikat."
    ),
    "15.13-02.md": (
        "Nvidia mengumumkan DLSS 4.5 dengan teknologi Ray Reconstruction yang ditingkatkan. Kabar baiknya, fitur ini bisa dinikmati di semua GPU RTX, tidak hanya seri terbaru.\n\n"
        "DLSS (Deep Learning Super Sampling) adalah teknologi AI Nvidia yang meningkatkan performa gaming dengan cara merender gambar di resolusi lebih rendah lalu mengup scalenya menggunakan AI.\n\n"
        "Versi 4.5 membawa peningkatan signifikan dalam kualitas ray tracing, membuat efek pencahayaan dan pantulan terlihat lebih realistis tanpa mengorbankan frame rate.\n\n"
        "Keputusan Nvidia untuk mendukung semua GPU RTX disambut positif oleh gamer, meskipun performa pastinya akan bervariasi tergantung generasi kartu grafis yang digunakan."
    ),
    "16.00-01.md": (
        "ByteDance, perusahaan induk TikTok, kehilangan pimpinan riset AI mereka — Gu Quanquan — yang memimpin pengembangan model Seed. Kepergiannya terjadi di tengah tekanan monetisasi AI.\n\n"
        "Gu Quanquan adalah otak di balik kesuksesan model AI Seed yang menjadi fondasi berbagai produk AI ByteDance. Kepergiannya merupakan pukulan berat bagi tim riset AI perusahaan.\n\n"
        "Tekanan untuk memonetisasi AI semakin besar seiring dengan meningkatnya biaya operasional dan persaingan dari rival seperti Baidu dan Alibaba.\n\n"
        "Kepergian talenta kunci ini menimbulkan pertanyaan tentang stabilitas dan masa depan riset AI di ByteDance, terutama di tengah ketidakpastian regulasi di China."
    ),
    "16.00-02.md": (
        "Saham Tencent melonjak 10 persen setelah kabar bahwa AI Agent akan segera hadir di WeChat, super app dengan 1,4 miliar pengguna. Ini bisa menjadi game-changer bagi ekosistem AI China.\n\n"
        "Integrasi AI Agent ke dalam WeChat akan memungkinkan pengguna mengakses layanan AI langsung dari platform chatting yang sudah mereka gunakan sehari-hari.\n\n"
        "Dengan basis pengguna yang sangat besar, WeChat bisa menjadi saluran distribusi AI paling masif di dunia, melampaui adopsi ChatGPT sekalipun.\n\n"
        "Langkah ini menunjukkan bahwa persaingan AI di China semakin memanas, dengan Tencent memanfaatkan ekosistem super app-nya untuk mempercepat adopsi AI."
    ),
    "17.06-01.md": (
        "Sebuah laporan dari BBC mengungkap bahwa banyak perusahaan yang kebingungan dalam menyusun strategi AI. Mereka terjebak dalam tren tanpa rencana yang jelas, membuat karyawan frustrasi.\n\n"
        "Fenomena 'FOMO AI' melanda banyak perusahaan — mereka merasa harus mengadopsi AI tanpa benar-benar memahami bagaimana teknologi ini bisa memberi nilai tambah bagi bisnis mereka.\n\n"
        "Akibatnya, investasi AI sering kali tidak efektif, malah menambah beban kerja karyawan yang harus belajar alat baru tanpa dukungan yang memadai.\n\n"
        "Para ahli menyarankan perusahaan untuk mundur sejenak, mengevaluasi kebutuhan nyata, dan membuat roadmap AI yang terstruktur sebelum berinvestasi besar-besaran."
    ),
    "18.09-01.md": (
        "Tripo AI berhasil mengumpulkan dana hampir USD 200 juta untuk mengembangkan AI 3D dan world model. Project Eden, proyek andalan mereka, kabarnya bisa menciptakan dunia virtual secara otomatis.\n\n"
        "Pendanaan besar ini menunjukkan keyakinan investor terhadap potensi AI generatif 3D, yang dianggap sebagai langkah berikutnya setelah kesuksesan AI teks dan gambar.\n\n"
        "Project Eden menggunakan pendekatan world model — AI yang memahami fisika dan logika dunia nyata — untuk menciptakan lingkungan virtual yang realistis.\n\n"
        "Teknologi ini punya potensi aplikasi luas, mulai dari game, film, arsitektur, hingga simulasi pelatihan untuk robot dan kendaraan otonom."
    ),
    "18.09-03.md": (
        "Para peneliti keamanan menemukan jenis backdoor AI baru yang dinamakan BadBone. Teknik ini bisa membobol sistem AI tanpa terdeteksi, bahkan enam tools keamanan terkemuka gagal mengenalinya.\n\n"
        "BadBone bekerja dengan menyusup ke dalam model AI melalui data training yang telah dimanipulasi, menanamkan pintu belakang yang baru aktif saat trigger spesifik diberikan.\n\n"
        "Yang lebih mengkhawatirkan, backdoor ini dirancang untuk lolos dari deteksi tools keamanan AI standar, membuatnya sangat sulit ditemukan bahkan setelah model sudah di-deploy.\n\n"
        "Temuan ini menjadi alarm keras bagi industri AI untuk segera mengembangkan metode deteksi dan pertahanan yang lebih canggih terhadap serangan semacam ini."
    ),
    "19.00-01.md": (
        "Walmart mulai membatasi pemakaian AI oleh karyawannya. Token AI yang diberikan kepada karyawan mulai dibatasi karena biaya AI membengkak di luar kendali.\n\n"
        "Sebagai salah satu perusahaan dengan jumlah karyawan terbesar di dunia, Walmart menghadapi tantangan unik: biaya langganan AI untuk ratusan ribu karyawan bisa mencapai angka yang sangat besar.\n\n"
        "Pembatasan ini menuai beragam reaksi — sebagian karyawan kecewa karena sudah terbantu dengan alat AI, sementara manajemen melihatnya sebagai langkah fiskal yang diperlukan.\n\n"
        "Kasus Walmart menjadi contoh bagaimana biaya operasional AI bisa menjadi beban serius bagi perusahaan besar, memicu pertanyaan tentang keberlanjutan model bisnis AI saat ini."
    ),
    "20.07-02.md": (
        "ZeroDrift, sebuah startup keamanan AI, berhasil mengumpulkan $10 juta untuk mengembangkan solusi yang melindungi model AI dari 'dirinya sendiri' — mencegah AI berperilaku di luar kendali.\n\n"
        "Produk ZeroDrift fokus pada AI compliance dan safety, memastikan bahwa model AI generatif beroperasi dalam batasan yang telah ditentukan dan tidak menghasilkan output yang berbahaya.\n\n"
        "Pendekatan yang mereka tawarkan menjadi semakin relevan seiring dengan meningkatnya kekhawatiran tentang AI hallucination, bias, dan potensi penyalahgunaan.\n\n"
        "Investasi ini menandakan bahwa pasar untuk keamanan AI semakin matang, dengan investor mulai melihatnya sebagai sektor yang penting dan menguntungkan."
    ),
    "20.07-03.md": (
        "Impulse, sebuah startup rocket engine, berhasil mengumpulkan $500 juta dengan pendekatan yang unik: mereka memilih merekrut manusia, bukan AI. Ini adalah anti-tesis dari tren industri saat ini.\n\n"
        "Di saat hampir semua perusahaan teknologi berlomba mengadopsi AI, Impulse justru percaya bahwa sentuhan manusia tetap tak tergantikan dalam industri aerospace yang penuh risiko tinggi.\n\n"
        "Pendekatan human-centric ini ternyata menarik minat investor yang melihat nilai dalam keahlian dan judgment manusia untuk tugas-tugas yang membutuhkan presisi dan keamanan ekstrem.\n\n"
        "Keberhasilan Impulse membuktikan bahwa di era AI, investasi pada sumber daya manusia tetap bisa menjadi strategi yang menarik dan menguntungkan."
    ),
    "20.07-01.md": (
        "Google memperkenalkan Gemini Spark, AI agent yang bisa bekerja 24/7 tanpa henti. Deskripsi dari para penguji awal: paling mengesankan sekaligus paling menyeramkan yang pernah mereka lihat.\n\n"
        "Gemini Spark mampu menjalankan tugas-tugas kompleks secara mandiri — mulai dari merencanakan perjalanan, mengelola email, hingga menulis kode — tanpa perlu campur tangan manusia.\n\n"
        "Kemampuannya yang bekerja non-stop membuat produktivitas melonjak drastis, namun juga menimbulkan pertanyaan etis tentang batasan otonomi AI.\n\n"
        "Google mengklaim telah menerapkan safety measures yang ketat, namun para kritikus tetap khawatir tentang implikasi AI agent yang bisa bertindak secara independen dalam jangka panjang."
    ),
    "21.06-01.md": (
        "MiniMax M3, model AI dari China, berhasil mengalahkan GPT-5.5 dan Gemini 3.1 Pro dalam berbagai benchmark — dengan biaya hanya 5-10 persen dari kompetitor. Ini adalah pencapaian yang luar biasa.\n\n"
        "Efisiensi biaya yang ekstrem ini dicapai melalui arsitektur model yang inovatif dan teknik optimasi training yang revolusioner, memungkinkan performa tinggi dengan sumber daya komputasi minimal.\n\n"
        "Keberhasilan MiniMax M3 menjadi bukti bahwa persaingan AI global semakin ketat, dengan pemain China mampu menawarkan alternatif berperforma tinggi dengan harga jauh lebih murah.\n\n"
        "Ini bisa memicu perang harga di industri AI dan mempercepat demokratisasi akses ke model AI canggih, meskipun juga menimbulkan pertanyaan tentang keberlanjutan model bisnis berbasis langganan mahal."
    ),
    "21.06-02.md": (
        "Anthropic merilis data keamanan yang mengejutkan: browser AI Claude bisa dibajak dengan tingkat keberhasilan 31,5 persen hanya dalam sekali percobaan. Temuan ini membuka mata industri.\n\n"
        "Kerentanan ini memungkinkan penyerang untuk memanipulasi Claude agar melakukan tindakan yang tidak diinginkan saat mengakses web melalui browser AI.\n\n"
        "Anthropic secara transparan mempublikasikan temuan ini sebagai bagian dari komitmen mereka terhadap AI safety, meskipun data ini bisa dimanfaatkan oleh pihak jahat.\n\n"
        "Langkah ini menunjukkan bahwa transparansi tentang kelemahan AI adalah pedang bermata dua — penting untuk perbaikan, namun juga bisa dieksploitasi sebelum patch dirilis."
    ),
    "22.05-01.md": (
        "Anthropic memperluas Claude Mythos — sistem AI untuk infrastruktur kritis — ke 15 negara, dengan NATO dan Samsung menjadi klien utama. Ekspansi ini menandai langkah besar Anthropic ke sektor enterprise.\n\n"
        "Claude Mythos dirancang khusus untuk menangani beban kerja infrastruktur kritis seperti energi, telekomunikasi, dan pertahanan — area dengan tingkat risiko dan regulasi yang sangat ketat.\n\n"
        "Keterlibatan NATO menunjukkan kepercayaan tinggi terhadap keamanan dan keandalan Claude Mythos, menjadi endorsement yang sangat berharga bagi Anthropic.\n\n"
        "Ekspansi ini menempatkan Anthropic dalam persaingan langsung dengan perusahaan-perusahaan enterprise AI mapan, dan membuka pasar baru yang sangat besar."
    ),
    "22.05-03.md": (
        "Claude Mythos kembali menjadi sorotan — kali ini mengungkap fakta pahit tentang proses patching di perusahaan: terlalu lambat. Eksploitasi bisa terjadi hanya dalam 9 jam setelah kerentanan ditemukan.\n\n"
        "Laporan dari VentureBeat mengungkap bahwa rata-rata perusahaan membutuhkan waktu berhari-hari hingga berminggu-minggu untuk menambal kerentanan keamanan, sementara penyerang bisa mengeksploitasi dalam hitungan jam.\n\n"
        "AI Mythos milik Anthropic membantu mengidentifikasi celah-celah ini secara real-time, tapi tanpa respons yang cepat, deteksi saja tidak cukup.\n\n"
        "Temuan ini menjadi wake-up call bagi enterprise untuk mempercepat proses security patching mereka, terutama di era di mana serangan siber semakin otomatis dan cepat."
    ),
}

written = []
skipped = []

for i, article in enumerate(articles):
    fname = article["file"]  # e.g., "2026-06-02/12.00-01.md"
    rel_path = f"{BASE}/{fname}"
    thumb_file = fname.split("/")[-1]  # just the filename part
    
    # Skip if exists
    if os.path.exists(rel_path):
        skipped.append(fname)
        continue
    
    # Get category
    cat = CATEGORIES.get(thumb_file, "Industry & Business")
    
    # Get title
    title = TITLES.get(thumb_file, " — ".join(article["thumb_lines"]))
    
    # Get caption
    caption = CAPTIONS.get(thumb_file, "\n\n".join(article["thumb_lines"]))
    
    # Build content
    content = f"# {i+1} — {cat}\n\n---\n\n## {title}\n\n{caption}\n\n![Ilustrasi]({article['thumb_image']})\n\n**Sumber:** [{article['source']}]({article['url']})\n"
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(rel_path), exist_ok=True)
    
    # Write file
    with open(rel_path, "w") as f:
        f.write(content)
    written.append(fname)

print(f"=== RESULT ===")
print(f"Written: {len(written)} files")
print(f"Skipped (already exist): {len(skipped)} files")
print(f"\n--- Written Files ---")
for w in written:
    print(w)
print(f"\n--- Skipped Files ---")
for s in skipped:
    print(s)
