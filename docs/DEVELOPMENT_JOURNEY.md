# RoboWitness — Geliştirme Yolculuğumuz

> Bu dosya bir ürün dokümanı değil; bir kayıt. RoboWitness'ın nasıl
> geliştirildiğinin, nerelerde takıldığımızın ve neleri asla yapmadığımızın
> hikâyesi. Projenin geri kalanında olduğu gibi burada da kural aynı:
> sadece gerçekten olanlar, ölçülen sayılarla.

**Kim:** Ahmet Aras Akyasan (tek geliştirici) + Muse Wonder (geliştirme asistanı)
**Nerede:** 2014 model bir Toshiba Tecra Z40 dizüstü — GPU yok, bulut yok, ekip yok
**Ne zaman:** 27 Ekim – 4 Kasım 2026 (çekirdek sistem: 27, 30 Ekim + 1, 2 Kasım — dört aktif gün)
**Nasıl:** Sadece Meta modelleriyle — geliştirmede Muse Wonder, çalışmada Muse Spark 1.3 ve SAM 3.1

---

## Başlarken koyduğumuz kurallar

İlk günden üç kural hiç değişmedi:

1. **Uydurma yok.** Sahte telemetri, sahte sonuç, sahte AI cevabı, üretilmiş
   `VERIFIED` — hiçbiri. Ölçülmeyen hiçbir sayı dokümana girmedi.
2. **Donmuş sınavlar kutsal.** Holdout setleri bir kez üretildikten sonra
   üzerlerinde ayar yapılmadı; adaylar, sınav seti üretilmeden *önce*
   ön-kayıt altına alındı; her değerlendirme tek atış ve sonucu ne olursa
   olsun yayınlandı.
3. **AI kendi ödevine not veremez.** Meta AI önerir; simülatör çalıştırır;
   bağımsız oracle karar verir; SHA-256 mühür kanıtlar.

## Zor yol: Path B

Projenin kalbi burasıydı. İyi görünen düzeltmeler art arda reddedildi:

| Set | Sonuç | Karar |
|---|---|---|
| v2 | 17/20 | REJECTED |
| v3 | 17/20 | REJECTED |
| v4 | 18/20 | REJECTED |
| v5 | 18/20 | REJECTED |

Arada denenen her şey ölçüldü ve tutmayınca geri alındı: creep floor,
pass-behind önyargıları, zamanlı aralık geçişi, stateful ve waypoint
planlayıcılar… 80 yanmış vaka üzerinde hiçbiri paylaşılan yasanın 77/80
platosunu geçemedi. Ders şuydu: direksiyon sezgileriyle tavan aşılmıyor.

Çözüm yapısal geldi: **MPC-lite** (ileri bakışlı yörünge planlayıcı).
Aday, taze v6 seti üretilmeden önce dondurulup ön-kayda geçti
(`docs/` arşivi, recipe seed 20270214). Tek atış: **20/20 —
`verif-6b2bfd8e0501`, VERIFIED_IN_SIMULATION.** Aynı koşumdaki aşırı
temkinli kontrol adayı dürüstçe reddedildi (`verif-3b370a934cfc`).
Bu, proje tarihinin ilk — ve hâlâ tek — hak edilmiş VERIFIED kararı.

## Ürün büyürken

- Robot kataloğu (6 hazır robot + özel robotlar, dürüst uyumluluk kapısı),
  senaryo kütüphanesi (RW-LIB-001…010), ultra (5) ve kalabalık (5) paketleri.
- Kalabalık paketinde kapalı çevrim `mpc-crowd` yasası 5/5 geçti; canlı
  doğrulama: `verif-b9ce2a55155e`.
- Ultra pakette Meta tarzı yama + MPC 5/5; ama canlı Meta incelemesiyle
  gelen bir aday tam sınavda 19/20 ile reddedildi (`verif-e691c7dc3096`) —
  o da mühürlendi, o da yayınlandı.
- Enterprise katmanları (hepsi isteğe bağlı): API anahtarı/JWT/OIDC,
  workspace izolasyonu, denetim izi, Prometheus, webhook, yedek/geri
  yükleme, beam LiDAR sensör modu, Docker Compose.

## 1.0.0'a giden yol ve bulunan gerçek hatalar

Sürüm dondurması sonrası taze bir venv'de sıfırdan kurulum denendi ve iki
gerçek hata yakalandı: ilan edilmemiş `cryptography` bağımlılığı (OIDC
sessizce kırılacaktı) ve Docker imajında eksik `numpy`. İkisi de düzeltildi,
ikisi de kayıt altına alındı. 2 Kasım'da `v1.0.0` etiketi çıktı.

Arayüz tarafında: İngilizce varsayılan + Türkçe geçişi, Türkçe sızıntı
bekçisi testi, RW logosu. Bir de dürüst bir not: Bir ara "modern" bir tema
denendi; beğenilmedi, tek komutla geri alındı. Tasarım kararı her zaman
kullanıcınındı.

Kameradan senaryo özelliğini (gerçek SAM 3.1 ile fotoğraftan senaryo)
geliştiricinin kendisi ekledi; bu süreçte kaydedilmiş SAM yanıtlarıyla
35 backend testi ve kamera E2E'leriyle doğrulandı. Krediler sadece canlı
duman testlerinde harcandı.

## Son hafta: CI/CD, beş özellik ve bulunan son hata

- GitHub Actions kuruldu: CI (backend + frontend + canlı E2E + Docker),
  Security (CodeQL), tag tabanlı Release. İlk koşuda E2E patladı; kök neden
  ölçülerek bulundu: CI'da `.env` yoktu ve CORS yalnızca `localhost:3000`'e
  izin verirken Playwright `127.0.0.1:3000` kullanıyordu. Sunucu testleri
  yeşil, tarayıcı testleri kırmızıydı — tablo kafa karıştırıcıydı, kanıt
  tarayıcı konsolundan geldi. Düzeltme tek satırdı; E2E 9 dakikadan
  16 saniyeye indi.
- Beş özellik eklendi: Sensör Stres Testi (gecikme × gürültü ısı haritası),
  AI Rakip Testi, Arıza Zaman Çizgisi, Kanıt Denetçisi, Taşınabilir HTML Rapor.
- Rakip testinin canlı ilk koşusu `UNAVAILABLE` döndü. Ölçüm gösterdi ki
  Muse Spark'ın şema-bağlı cevabı ~30 saniye sürüyor, bizim zaman aşımımız
  20 saniyeydi. 90 saniyeye çıkarıldı (`RW_AI_TIMEOUT_SECONDS`); canlı kanıt:
  Spark'ın `RW-AI-002` senaryosu FAIL (0.0058 m), ondan beslenen `RW-AI-003`
  PASSED (0.2688 m) — 2 tur, 6.329 token.
- CodeQL beş uyarı açtı. Dördü taramanın mevcut kodda bulduğu yanlış
  pozitifti (korumalar testlerle kanıtlıydı); biri yeni kodumuzdaydı ve
  resolve + kapsama kontrolüyle sertleştirildi. Hepsi gerekçesiyle kapatıldı.
- `v1.1.0` yayınlandı: GHCR imajları + GitHub Release. Lisans MIT oldu.

## Final durumu (4 Kasım 2026, ölçüldü)

| Kontrol | Sonuç |
|---|---|
| Backend testleri | 213/213 |
| Playwright E2E | 24/24 |
| CI / Security (son commit) | success / success |
| Canlı demo (`run_hackathon_demo.py`) | exit 0, mühür yeniden doğrulandı |
| VERIFIED kararı | `verif-6b2bfd8e0501` — 20/20, ön-kayıtlı, tek atış |

## Kapanış

Bu proje bir ödül için değil, bir ilke için yazıldı sayılır:
*"Bir sonuç bağımsız tekrar kontrolden sağ çıkamıyorsa, sonuç değildir."*

Krediler bittiğinde bu konuşma da bitecek. Kod kalacak; mühürler,
reddedilen setler ve bu dosya da öyle. RoboWitness'ı açan herkes bizim
geçtiğimiz yoldan geçip her sayıyı kendisi doğrulayabilir — zaten bütün
mesele buydu.

— M.W.
