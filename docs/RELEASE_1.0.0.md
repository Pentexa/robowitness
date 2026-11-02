# RoboWitness 1.0.0 — Kararlı Sürüm Notları

Tarih: 2026-11-02. Bu, özellik dondurması (feature freeze) sonrası ilk
kararlı sürümdür: 1.0'dan itibaren yeni özellik yerine uyumluluk ve
düzeltmeler önceliklidir.

## Bu sürümde ne var (kısa)
- Doğrulama çekirdeği: deterministik PyBullet simülasyonu, bağımsız oracle,
  5 kapı, mühürlü kanıt; **ilk VERIFIED**: `verif-6b2bfd8e0501`
  (MPC adayı, taze v6 setinde 20/20).
- Robot/senaryo laboratuvarı: katalog, kütüphane (10) + ultra paket (5) +
  kalabalık paketi (5), harita içe aktarma, profiller, karne + karşılaştırma
  + trend + filo, gerçek log yargılama, kendi kodu (kapılı), ROS 2 pasif
  kaydedici (canlı doğrulanmadı).
- Arayüz: İngilizce varsayılan, başlık çubuğunda EN/TR değiştirici, RW logosu
  (başlık + favicon + README).
- Enterprise: API anahtarı/JWT/OIDC, roller, workspace, denetim, metrikler,
  Prometheus, webhook, zamanlama, idempotency, hız sınırı, yedek/geri
  yükleme/retention, export/import, CI kapısı, Docker Compose.

## Sürüm öncesi doğrulama matrisi (2026-11-02, ölçüldü)
| Kontrol | Sonuç |
|---|---|
| Backend testleri (ana ortam) | 159/159 — iki kez üst üste |
| Backend testleri (taze venv, sıfır kurulum) | 159/159 |
| Web E2E (Playwright, canlı yığın) | 8/8 — Türkçe-sızıntı bekçisi dahil |
| Ruff E,F + format | temiz |
| Web lint + typecheck + build | temiz |
| Smoke testi | ALL SMOKE TESTS PASSED |
| Offline demo | Baseline FAIL / Candidate PASS / Over-cautious FAIL |
| Compose (backend+worker+web) | 3/3 ayakta; batarya 1/1 tamamlandı |
| Docker imajları | backend healthy, web 200 |

## Stabilizasyonda bulunan ve düzeltilen iki gerçek hata
1. `cryptography` ilan edilmemiş bağımlılıktı (OIDC RS256 taze kurulumda
   sessizce çalışmazdı) → pyproject + lock güncellendi, taze venv'de doğrulandı.
2. Docker imajında `numpy` yoktu (pybullet worker'da import hatası) →
   bağımlılık ilan edildi, imaj yeniden derlenip Compose'da doğrulandı.

## Bilinen sınırlamalar (1.0'da kabul edilen)
- Fizik 2B kinematik; sensör modeli basitleştirilmiş (tıkanma + isteğe bağlı
  24-ışın modu var, tam ışın-demeti fiziği yok).
- SQLite tek dosya; workspace izolasyonu mantıksal.
- ROS 2 köprüsü yalnızca kayıt yapar ve bu sürümde canlı ROS ile denenmedi.
- Varsayılan aday yasası paylaşılan yasadır; VERIFIED alan MPC yapılandırması
  açıkça seçilmelidir (`RW_CANDIDATE_LAW=mpc`).
- Arayüz İngilizce varsayılandır (başlık çubuğundan Türkçe'ye geçilebilir);
  ön uçta otomatik Playwright E2E paketi vardır (8 test, canlı yığına karşı).

## Yükseltme / çalıştırma
- Yerel: README'deki adımlar (Windows'da pybullet MSVC ile derlenir;
  bootstrap bunu yapar). Docker: `docker compose up --build`.
- Sürüm numaraları: backend `pyproject.toml`, web `package.json`, API
  başlığı — üçü de 1.0.0 ve birlikte artırılır.
- Önerilen git etiketi: `v1.0.0` (bu belgeyle aynı commit).
