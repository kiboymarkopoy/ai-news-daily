# VPS Bandwidth Tunnel — Analisis Kelayakan & Plan

## 🎯 Goal
Parekso ingin menggunakan bandwidth VPS (DigitalOcean SGP1) sebagai tunnel internet untuk HP Android-nya, supaya quota seluler tidak terpakai.

## 📊 Analisis Jujur: Apakah Masuk Akal?

### ✅ MASUK AKAL — dengan catatan

**Yang sudah terbukti bekerja:**
- TailScale exit node → BERHASIL. Parekso sudah tes nonton YouTube 16K 2 menit, quota HP tidak berkurang.
- IP forwarding VPS aktif, NAT rules benar, TailScale sudah dikonfigurasi sebagai exit node.

**Yang GAGAL:**
- WireGuard standalone → Handshake = 0, RX = 0, TX = 0. HP tidak pernah berhasil connect.

### 🔍 Root Cause Analisis: Kenapa WireGuard Gagal

| Faktor | Penjelasan |
|--------|-----------|
| **DigitalOcean Cloud Firewall** | DO punya firewall di level cloud (SEBELUM packet sampai ke VPS). Kalau UDP 51820 tidak di-allow di DO dashboard → packet di-drop sebelum sampai ke iptables/UFW. Ini TIDAK bisa dideteksi dari dalam VPS. |
| **Carrier NAT (CGNAT)** | Provider seluler Indonesia (Telkomsel, XL, Indosat) hampir semua pakai CGNAT. UDP bisa di-restrict atau di-throttle oleh carrier. TailScale mengatasi ini dengan DERP relay server + hole punching — WireGuard murni TIDAK punya fallback. |
| **Android VPN conflict** | Android hanya mengizinkan 1 VPN aktif. Kalau TailScale masih jalan saat WireGuard dinyalakan → salah satu gagal. |
| **QR code scan issue** | Bisa jadi config tidak ter-import dengan benar di app WireGuard HP. |

### 💡 Kesimpulan

**TailScale exit node SUDAH BEKERJA.** Tidak perlu WireGuard.

Masalah yang Parekso khawatirkan (quota bocor) sudah terjawab:
- Saat exit node aktif + APN IPv4 only → quota HP aman
- Satu-satunya risiko: tunnel drop sementara karena Android kill background apps

---

## 📋 Plan: Solusi Optimal

### Opsi A: Tetap Pakai TailScale Exit Node ⭐ RECOMMENDED
**Effort:** Sudah jalan, tinggal hardening.

**Steps:**
1. Pastikan TailScale di HP di-set "Unrestricted" battery optimization
2. Disable battery optimization untuk TailScale (Settings → Apps → TailScale → Battery → Unrestricted)
3. Lock TailScale di recent apps (tekan lama → Lock)
4. Test ulang: nonton YouTube 30 menit, cek quota sebelum dan sesudah
5. (Opsional) Cek di DO dashboard apakah ada cloud firewall yang membatasi bandwidth

**Pro:**
- Sudah terbukti bekerja
- Auto reconnect, DERP relay fallback
- Gak perlu setup tambahan

**Con:**
- Tidak ada kill switch di Android (traffic bisa bocor ke mobile data saat tunnel drop)
- Bergantung pada TailScale coordination server (rare downtime)

### Opsi B: WireGuard via TailScale Subnet (Hybrid)
**Effort:** Medium. Setup WireGuard tunnel MELALUI TailScale network.

**Steps:**
1. Buat WireGuard tunnel di atas TailScale network (endpoint = 100.71.62.75 bukan IP publik)
2. Ini menghindari masalah cloud firewall dan CGNAT
3. Tapi ini overkill — pada dasarnya TailScale exit node sudah melakukan hal yang sama

**Verdict:** Overkill, skip.

### Opsi C: Outline VPN (Shadowsocks-based)
**Effort:** Low. Docker compose di VPS, scan QR dari HP.

**Steps:**
1. `docker compose up` Outline server di VPS
2. Generate access key
3. Install Outline app di HP
4. Scan QR / paste key
5. Outline app punya kill switch di Android

**Pro:**
- Kill switch bawaan di Android app
- Shadowsocks-based → lebih tahan terhadap carrier throttling
- Mudah share ke orang lain (generate key baru)

**Con:**
- Perlu Docker (sudah ada di VPS)
- Satu layer tambahan

### Opsi D: WireGuard Fix (Cek DO Firewall + Direct Setup)
**Effort:** Medium. Perlu akses DO dashboard.

**Steps:**
1. Login ke DigitalOcean dashboard
2. Cek Networking → Firewalls → apakah ada firewall yang di-attach ke droplet belajar-dev
3. Kalau ada: tambahkan rule Allow Inbound UDP 51820
4. Kalau tidak ada firewall: masalahnya kemungkinan di carrier CGNAT
5. Test ulang dari HP
6. Kalau masih gagal → carrier CGNAT confirmed → WireGuard murni tidak cocok untuk mobile Indonesia

---

## 🏆 Rekomendasi Final

| Priority | Opsi | Action |
|----------|------|--------|
| 1️⃣ | **TailScale Exit Node** | SUDAH JALAN. Hardening battery + lock app. |
| 2️⃣ | **Outline VPN** | Setup sebagai BACKUP. Punya kill switch. |
| 3️⃣ | **WireGuard fix** | HANYA kalau mau — cek DO dashboard firewall dulu. |

**Bottom line:** Lo SUDAH punya solusi yang bekerja (TailScale). Gak perlu bikin yang baru. Yang perlu dilakukan cuma hardening supaya tunnel gak drop.

---

## ⚠️ Cleanup Needed
- Hapus WireGuard config dan rules yang sudah dibuat (kalau tidak dipakai)
- Hapus debug iptables LOG rules
- Kembalikan iptables ke state bersih

## 🔢 Bandwidth VPS — Perlu Dicek
- DigitalOcean droplet biasanya punya **bandwidth allowance** (biasanya 1-6 TB/bulan tergantung plan)
- Kalau Parekso streaming YouTube tiap hari lewat VPS, bisa kena overage charge
- **Action:** Cek di DO dashboard → Droplet → Bandwidth tab
