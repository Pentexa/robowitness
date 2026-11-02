# RoboWitness Enterprise Kılavuzu

Bu belge, yerel tek-kullanıcı modunun üzerindeki enterprise katmanı anlatır.
Her özellik **isteğe bağlıdır**: hiçbiri açılmadan sistem eskisi gibi çalışır.

## 1. API anahtarı, rol ve çalışma alanı (workspace)

`.env` içinde (bkz. `.env.example`):

```
RW_API_KEYS=anahtar1:admin:depo-a;anahtar2:editor:depo-a;anahtar3:viewer:depo-a
```

- Boş bırakılırsa: açık yerel mod (kimlik gerekmez, aktör `local`).
- Doluysa: `/api/health` hariç tüm `/api` çağrıları `X-API-Key` başlığı ister.
  Anahtarsız → 401, yanlış anahtar → 401, `viewer` ile yazma → 403.
- Roller: `admin` (her şey + denetim kaydı) > `editor` (okuma+yazma) > `viewer` (okuma).
- Çalışma alanı izolasyonu: kullanıcı robotları, politika profilleri, karneler ve
  gerçek sürüş içe aktarımları anahtarın workspace'inde izole edilir. Anahtarsız
  modda `X-Workspace-Id` başlığı aynı işlevi görür. Hazır kataloglar (robotlar,
  profiller) tüm alanlarda paylaşılır.
- Tarayıcı: üst çubuktaki "API key (if any)" ve "Workspace" alanları değerleri
  `localStorage`'da saklar; anahtar koda ASLA yazılmaz.

## 2. Denetim kaydı (audit) ve metrikler

- Her yazma isteği (POST/PUT/DELETE) `audit_logs` tablosuna aktör, rol, workspace,
  yol ve durum koduyla yazılır. Okuma: `GET /api/audit?limit=50` (admin).
- `GET /api/metrics`: workspace sayıları, son karne özeti, içe aktarma
  geçme/kalma sayıları, koşu/doğrulama toplamları, iş durumları.

## 3. Karne karşılaştırma

`GET /api/batteries/compare?a=<id>&b=<id>` — senaryo başına
PASS/FAIL değişimi, mesafe farkı ve özet deltası döner.
Arayüzde (İngilizce): Report Card sekmesi → "Report Card Comparison (A → B)".

## 4. Kendi ortamım: harita ve kamera içe aktarma

`POST /api/maps/scenario` — ızgara metni (`#` engel, `.` boş, `S` başlangıç,
`G` hedef) + hücre boyutu → doğrulanmış senaryo. Her bağlantılı engel kümesi bir
daire engele çevrilir (en çok 8; kırpılmalar uyarı olarak döner). Dünya boyutu
6–20 m × 4–15 m sınırına uymalı. Arayüzde: Test sekmesi → "Scenario From My Map".

`POST /api/scenarios/from-image/detect` + `POST /api/scenarios/from-image/scenario` —
kamera/fotoğraftaki nesneleri gerçek SAM 3.1 ile tespit edip (ölçek + overhead
onayı zorunlu) kaydedilebilir, çalıştırılabilir senaryoya çevirir
(`GET /api/scenarios/from-image/saved`). Fotoğraflar sunucuda tutulmaz;
yalnızca ölçülmüş kutular ve kaynak SHA-256 saklanır. Workspace izolasyonu
ve denetim bu uçlara da uygulanır.

## 5. CI kapısı

```powershell
$env:RW_API_URL="http://127.0.0.1:8000"; $env:RW_API_KEY="..."
python scripts/ci_battery_gate.py --robot robot-turtlebot3-waffle-pi `
  --policy-file policy.json --min-pass-rate 0.8 --max-collisions 0
```

Çıkış kodları: 0 kapı geçti, 1 eşik aşıldı (nedenler yazılır), 2 altyapı hatası.
Worker'ın çalışıyor olması gerekir (işler worker tarafından yürütülür).
Eşik mantığının kendisi `app/verification/battery_gate.py` içindedir ve
birim testiyle doğrulanır.

## 6. JWT / OIDC, yedek, trend, filo (ikinci enterprise turu)

- **JWT:** `Authorization: Bearer <token>` desteklenir. HS256 için
  `RW_JWT_SECRET`; OIDC/RS256 için `RW_OIDC_JWKS_URL` (+ isteğe bağlı
  `RW_OIDC_ISSUER`, `RW_OIDC_AUDIENCE`). Claim eşlemesi: `sub`→aktör,
  `role`→rol (tanınmazsa viewer), `workspace`→çalışma alanı. Süresi dolmuş,
  imzası bozuk veya gizli anahtarı yanlış token → 401. Tarayıcıda üst
  çubuktaki "JWT" alanına yapıştırılır.
- **Yedek/geri yükleme:** `GET /api/workspaces/export` (admin) alanın tüm
  kiracı verisini JSON paket olarak verir; `POST /api/workspaces/import`
  başka alana geri yükler (robot/profiller yeni kimlik alabilir; karne/log
  geçmişi asla ezilmez, çakışanlar atlanıp raporlanır).
- **Trend:** `GET /api/batteries/trend` geçme oranının zaman serisini verir;
  Report Card sekmesinde çubuk listesi olarak görünür.
- **Filo bataryası:** `POST /api/batteries/fleet` birden çok robot için tek
  istekle batarya kuyruğa alır; uyumsuz/bilinmeyen robotlar nedenleriyle
  atlanır. Report Card sekmesinde sıralı filo sonucu görünür.
- **Sensör gerçekçiliği:** Artık bir engelin arkasındaki engel sensörde
  görünmüyor (ışın tıkanması/occlusion). Tek engelli referans senaryo
  bit-aynı kaldı; kütüphane karne sonuçları yeniden ölçülüp aynı bulundu.

## 6b. Platform katmanı (üçüncü enterprise turu)

- **Veritabanı anahtarları:** `POST /api/admin/api-keys` anahtar üretir (yalnızca
  özet saklanır, düz metin bir kez gösterilir), `GET` listeler, `DELETE` iptal
  eder. İlk anahtar oluştuğu anda kimlik zorunlu olur; kilitlenmeyi önlemek
  için ilk anahtar admin olmak zorundadır (422). Yönetim: **Admin** sekmesi.
- **Idempotency:** `POST /api/runs` ve `POST /api/batteries`,
  `Idempotency-Key` başlığıyla tekrarlanırsa aynı işi geri verir, çift koşu açmaz.
- **Sertleştirme:** her yanıtta `X-Request-Id`, `nosniff`, `X-Frame-Options:
  DENY`; `RW_RATE_LIMIT_PER_MIN` ile aktör başına hız sınırı (429).
- **Webhook:** `RW_WEBHOOK_URL` + `RW_WEBHOOK_SECRET` ayarlıysa iş/karne
  bitiminde HMAC-SHA256 imzalı (`X-RoboWitness-Signature`) bildirim gider;
  başarısız teslimat işi düşürmez.
- **Zamanlanmış batarya:** `POST /api/batteries/schedules` (en az 5 dk);
  worker zamanı geleni bir kez kuyruğa alır. Yönetim sekmesinden kurulur.
- **Yedek/retention:** `POST /api/admin/backup` tutarlı SQLite yedeği +
  SHA-256 verir; `POST /api/admin/retention` (varsayılan kuru çalıştırma)
  eski karne/log/denetim geçmişini siler — mühürlü kanıta dokunmaz.
- **Prometheus:** `GET /api/prom` (kimliksiz, sağlık gibi) iş/koşu sayaçları.
- **Worker eşzamanlılığı:** `RW_WORKER_CONCURRENCY=2` gibi; atomik claim
  sayesinde aynı iş iki kez çalışmaz.

## 6c. Dağıtım ve sensör modu (dördüncü tur)

- **Docker:** `docker compose up --build` (backend + worker + web; artefaktlar
  named volume'da). İmajlar bu makinede derlenip çalıştırılarak doğrulandı
  (backend healthy, web 200). Docker Desktop bu makinede kararsızdı; iki kez
  çöküp yeniden başlatıldı — imajlar yine de doğrulandı.
- **Sensör modeli:** `RW_SENSOR_MODEL=beam` 24 ışınlı LiDAR benzeri modu açar
  (kuantize kerteriz; ışın arasına düşen engel görülmez). Varsayılan `legacy`;
  tüm donmuş sonuçlar legacy ile ölçülmüştür. Beam modunda kütüphane desenleri
  aynı kaldı (LIB-005 mesafe 0.1492 vs legacy 0.152).
- **Yedekten dönüş:** `POST /api/admin/restore` önce güvenlik kopyası alır,
  sonra seçili yedeği SHA-256'sıyla geri yükler.

## 7. Dürüst sınırlar

- SQLite tek dosya: çok kullanıcılı yatay ölçek için tasarlanmadı; workspace
  izolasyonu mantıksaldır, ayrı veritabanı değildir (taşınabilirlik için
  export/import var, parçalama/sharding yok).
- OIDC doğrulaması JWKS ile RS256'dır; IdP tarafı kurulumu (keşif/oturum
  yenileme) istemciye aittir, RoboWitness oturum yönetmez.
- Fizik hâlâ kinematik ve 2B'dir (tıkanma eklendi; isteğe bağlı 24-ışın
  LiDAR-benzeri modu da var); karneler gerçek dünya güvenlik onayı değildir.
- Path B **kapandı**: ön kayıtlı MPC-lite adayı taze v6 setinde 20/20 ile
  `VERIFIED_IN_SIMULATION` aldı (`docs/PATH_B_V6_PREREGISTRATION.md`).
  Varsayılan aday yasası paylaşılan yasadır; MPC açıkça seçilir.
