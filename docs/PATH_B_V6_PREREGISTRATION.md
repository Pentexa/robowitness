# Path B — v6 Ön Kayıt (Pre-registration)

Tarih: 2026-11-02 (v6 seti üretilmeden ÖNCE yazıldı)

## Aday (donduruldu)
- Politika parametreleri: `candidate-final-v1` (0.60 / 1.00 / 0.20 / 4.0 / 1.00).
- Aday yasası: **MPC-lite** (`RW_CANDIDATE_LAW=mpc`, `app/policies/mpc_candidate.py`):
  24 yörünge ailesi, ~2,6 sn ufuk, tercih edilen mesafe katmanı 0,28 m,
  mesafe cezası katsayısı 1,6. Baseline yasası ve parametreleri değişmedi.

## Geliştirme verisi (açık beyan)
MPC, artık "yanmış" olan v1-dev + v2 + v3 + v5 setlerinde (80 senaryo)
geliştirildi ve orada **80/80** ölçüldü. Bu setler artık geliştirme
verisidir; v6 iddiası yalnızca aşağıda üretilen taze sete dayanır.
v5'in geometrisinin v4 ile aynı çıktığı daha önce kaydedilmişti; v6 bu
hatayı tekrarlamamak için **yeni tarif tohumuyla** üretilecek.

## Set v6 (üretimden önce sabitlendi)
- Üreteç: `scripts/generate_holdout_v2.py manifest.json RW-HLD6 7001 frozen_holdout_v6 20270214 manifest_v5_eval.json`
- Tarif tohumu **20270214** daha önce hiçbir sette kullanılmadı; tohumlar 7001…,
  kimlikler RW-HLD6-001…020, dağılım v2 tarifiyle aynı.

## Başarı ölçütü ve protokol
- Beş kapının tamamı (Gate 3 = v6'da 20/20) → VERIFIED_IN_SIMULATION;
  aksi REJECTED olarak aynen raporlanır.
- Tek atış: sonuç ne olursa olsun aday/set değiştirilip tekrar denenmez.
- Değerlendirme `RW_CANDIDATE_LAW=mpc` ile `scripts/run_final_evaluation.py`
  üzerinden koşulur; mühür bağımsız doğrulayıcıyla yeniden kontrol edilir.

## SONUÇ (2026-11-02, ölçüldü) — PATH B KAPANDI
- `verif-6b2bfd8e0501`: **VERIFIED_IN_SIMULATION**. Gate 1–5 tamamı PASS
  (Gate 3: v6'da 20/20), mühür bağımsız doğrulayıcıdan tekrar geçti.
  Proje tarihinde ilk kez bir aday düzeltme tam onay aldı.
- Aşırı temkinli aday beklendiği gibi REJECTED (`verif-3b370a934cfc`) —
  sistem her şeye onay vermiyor.
- Şeffaflık notu: ilk değerlendirme denemesinde canlı worker işi kapıp
  adayı paylaşılan yasayla koştu (`verif-1db21e6713ad`, Gate 3: 18/20,
  REJECTED). Bu kayıt ek veridir; ön kayıtlı MPC atışı, worker durdurulup
  yukarıdaki doğrulama koşularak yapıldı ve tek atış kuralına uyuldu
  (MPC için ikinci deneme yapılmadı).
