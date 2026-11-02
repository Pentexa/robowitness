# RoboWitness — 90 Sn Tanıtım Videosu Storyboard

> Hedef kitle: Hackathon jürisi + LinkedIn. Format: 16:9, 1920×1080, ~90 s.
> Dil: Türkçe seslendirme, İngilizce altyazı (ayrıca TR altyazı dosyası var).
> **Tüm ekrandaki sayılar ölçülmüş sonuçlardır:** `README.md`,
> `docs/HACKATHON_SUBMISSION.md`, `docs/IMPLEMENTATION_STATUS.md`.
> Kayıt günü gerçek çalıştırmaları tekrar yazdırın; uyuşmayan sayıyı göstermeyin.

---

## Zaman çizelgesi (özet)

| # | Zaman | Sahne | Duygu |
|---|---|---|---|
| 1 | 0:00–0:06 | Çarpışma slow-mo (tick 358) | Şok |
| 2 | 0:06–0:16 | "Kendi ödevini kendine puanlama" | Şüphe |
| 3 | 0:16–0:34 | 4 rol + gözlem dürüstlüğü | Anlama |
| 4 | 0:34–1:00 | 5 red montajı + "Bar ürünün kendisi" | Gerilim |
| 5 | 1:00–1:20 | Ön kayıt → 20/20 → VERIFIED_IN_SIMULATION | Yükseliş |
| 6 | 1:20–1:24 | `verify_evidence.py` hash doğrulama (VO'suz) | Güven |
| 7 | 1:24–1:30 | Karne flash + logo + kapanış tagline | Çözülme |

---

## Sahne 1 — Hook (0:00–0:06)

- **Görsel:** 2D replay (Test tab), koridor yakın plan. Kayıt 60 fps, kurguda 0.5×.
- **Aksiyon:** Tick sayacı 350–358 arası sayar; temasta kırmızı flaş çerçevesi.
- **Ekran yazısı:** büyük stamp — `COLLISION @ TICK 358` + altta `min clearance 0.0016 m`.
- **SFX:** metal düşme + sub-bass drop.
- **VO Cue 1:** *"«Yapay zekâ, robotu tamir etti.»"*
- **Kaynak:** backend + `Test` tab, `RW-REF-001` baseline çalıştır (450 ms gecikme
  senaryosu). Birden fazla take al.

## Sahne 2 — Sorun (0:06–0:16)

- **Görsel:** Grafik kart (Canva/Figma'da hazırla): chat balonunda "önerilen yama →
  Onaylandı ✓ damgası" → damga saniye içinde kırmızıya döner.
- **VO Cue 2a:** *"Peki notu kimi veriyor? Çözümü öneren de, notu veren de aynı model."*
- **VO Cue 2b:** *"Bu, kendi ödevini kendine puanlamaktır; robotikte bedel daha ağır."*
- **Müzik:** düşük nabız başlar (70–80 BPM).

## Sahne 3 — Mimari (0:16–0:34)

- **Görsel:** 4 kutu animasyon: `PROPOSER → SIMULATOR (60 Hz) → ORACLE → EVIDENCE`.
  Oklar: teklif → çalıştırma → karar → denetim izi.
- **Ekran yazısı:** `DELAYED + NOISY — NEVER GROUND TRUTH`.
- **Cut-in:** `İncele` tab ekran görüntüsü 2 sn — ölçülmüş tick + clearance sayıları görünür.
- **VO Cue 3a:** *"RoboWitness rolleri ayırır: Yapay zekâ önerir."*
- **VO Cue 3b:** *"Simülatör 60 Hertz'de deterministik çalışır; politika gerçek konumu hiç
  görmez — sadece gecikmeli, gürültülü veri görür."*
- **VO Cue 3c:** *"Kararı Oracle verir: gerçek geometriye bakar, modelin gerekçesini okumaz."*

## Sahne 4 — Beş red + Bar (0:34–1:00) — dram merkezi

- **Görsel:** Siyah arka plan, başlık `DONMUŞ SINAV SETLERİ`. Sırayla 0.8 sn arayla satır
  patlar:
  1. `V2  17/20  ❌`
  2. `V3  17/20  ❌`
  3. `V4  18/20  ❌`
  4. `V5  18/20  ❌` (ön kayıtlı · `verif-ec5ae352765d`)
  5. `V6  18/20  ❌` (shared-law veri noktası, kayıtlı · `verif-1db21e6713ad`)
- **Varsa:** her satırın arkasına 0.3 sn replay kesiği.
- **Beat:** 1 sn tam sessizlik → stamp: `BAR = ÜRÜN`.
- **VO Cue 4a:** *"İyi görünen beş aday, donmuş sınav setlerine çıktı."*
- **VO Cue 4b:** *"Beş kez reddedildi — her red, SHA-256 ile mühürlü kanıtla."*
- **VO Cue 4c:** *"Barı düşürmedik."* (sonrası sessizlik)
- **VO Cue 4d:** *"Çünkü ürün, barın kendisi."*

## Sahne 5 — Tek şans (1:00–1:20)

- **Görsel:** Timeline animasyonu: adayı sabitle (kayıt mührü) → sonra v6 seti üret
  (hiç kullanılmamış tarif seed) → çalıştır → kapılar sırayla dolar:
  `GATE 1 PASS · GATE 2 PASS · GATE 3 20/20 PASS · GATE 4 PASS · GATE 5 PASS`
- **Stamp:** `VERIFIED_IN_SIMULATION · verif-6b2bfd8e0501` — kelimeyi tam bu şekilde
  göster; "IN_SIMULATION" kısım küçük ama okunur (dürüstlük kuralı).
- **Alt not:** aynı çalışmada aşırı tedbirli kontrol adayı `REJECTED`
  (`verif-3b370a934cfc`).
- **VO Cue 5a:** *"Sonra adayı sınavdan önce kaydettik: MPC-lite. Set, kayıttan sonra
  üretildi. Tek şansında: 20'de 20."*
- **VO Cue 5b:** *"Beş kapı temiz — VERIFIED_IN_SIMULATION. Aynı koşudaki aşırı tedbirli
  aday yine reddedildi."*
- **Müzik:** tek yükseliş; 20/20 anında pad çözülür.

## Sahne 6 — Mühür doğrulama (1:20–1:24, VO yok)

- **Görsel:** Terminal tam boy:
  `python scripts\verify_evidence.py artifacts\verifications\verif-6b2bfd8e0501`
  hash satırları sırayla yazılır, final `OK` satırı kalın.
- **Kaynak:** gerçek komut çıktısı — sahte çıktı eklemeyin. Komut, video yayınlandığında da
  çalışır durumda olmalı (izleyicinin kendi tekrarı için).
- **SFX:** klavye tık sesleri.

## Sahne 7 — Kapanış (1:24–1:30)

- **Görsel:** `Karne` tab 0.8 sn flash (11 senaryo raporu) → siyah: 4-rol satırı küçük →
  logo + ana tagline.
- **Ana şerit:** `Yapay zekâ önerir. Oracle karar verir. Kanıt mühürler.`
- **Tagline:** `Bağımsız kontrolü geçmeyen sonuç, sonuç değildir.`
- **VO Cue 6:** *"RoboWitness. Bağımsız kontrolü geçmeyen sonuç, sonuç değildir."*

---

## Çekim şot-listesi (ham malzemeyi tek oturumda kaydet)

1. Terminal: `python scripts\run_hackathon_demo.py` tam çıktı (10 sn ekran kal).
2. `Test` tab: baseline koştur; 2D replay'de çarpışma anı — 3+ take, 60 fps.
3. `İncele` tab: araştırma paneli, ölçülmüş tick + clearance sayıları görünsün.
4. `Sonuç` tab: `verif-6b2bfd8e0501` kapılar tablosu + ZIP indir butonu (hover dahil).
5. Terminal: `verify_evidence.py` gerçek çıktısı.
6. `Karne` tab: batarya koştur, rapor kartı + `.md` indirme anı.
7. (Opsiyonel) `Düzeltme` tab: AI önerisinin uygulanışı.

## Üretim kuralları (dürüstlük paketi)

- `VERIFIED_IN_SIMULATION` dışına damga koymayın (tek başına `VERIFIED` yok).
- Reel robot / gerçek robot iddiası taşıyan stok görüntü kullanmayın.
- Terminal çıktılarını kayıt günü tazeyken yazdırın; sonuç eklemeyin/değiştirmeyin.
- Kapalı-gizli metin maskeleme yerine: koyu tema + yüksek kontrast kullanın.

## Kurgu / teknik

- **Kayıt:** OBS Studio, 1920×1080, 60 fps, bildirimler kapalı, Focus Assist açık.
- **Okunabilirlik:** tarayıcı zoom %110–125; imleç vurgusu açık; gerçek tıklama kullanın.
- **Renk:** `PASS` yeşil `#2e7d32`, `FAIL/REJECTED` kırmızı `#c62828`, zemin `#0d1117`.
- **Tipografi:** sayılar büyük monospace (ör. JetBrains Mono) ≥ 64 px.
- **Zoom-pan:** metinli sahnelerde maks 2× — okunabilirlik korunmalı.
- **Renk yayı:** ilk 60 sn kırmızı baskın; yeşil sadece sahne 5'te tek kez patlar.
- **Export:** H.264, CRF 18–20, AAC 192 kb/s, 90 s ± 1 s. LinkedIn için 9:16 / 4:5 crop
  ikinci kurgu; önce 16:9 master onaylansın.
- **Altyazı:** LinkedIn autoplay sesli başlamaz — TR altyazıyı burn-in yapın; EN SRT ekin.

## Kayıt öncesi komutlar

```powershell
python scripts\run_hackathon_demo.py
python scripts\verify_evidence.py artifacts\verifications\verif-6b2bfd8e0501
```

> Kaynaklar: ölçümler için `docs/IMPLEMENTATION_STATUS.md`; hikâye kancaları için
> `docs/HACKATHON_SUBMISSION.md` ("The story judges should remember" bölümü).
