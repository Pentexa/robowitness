# Path B — v5 Ön Kayıt (Pre-registration)

Tarih: 2026-11-02 (v5 seti üretilmeden ÖNCE yazıldı)

## Aday (donduruldu, v5 sonuçlarına göre DEĞİŞTİRİLMEYECEK)
`candidate-final-v1`: max_speed 0.60, safe_distance 1.00, reaction_margin 0.20,
brake_gain 4.0, obstacle_prediction_horizon 1.00.
Gerekçe: yalnızca v1-dev (geliştirme) seti üzerinde seçildi; v2/v3/v4'te
sırasıyla 17/20, 17/20, 18/20 aldı. Bu deneme adayı yeniden ayarlamak için
değil, aynı adayın görmediği taze bir sette tek atışta ölçülmesi içindir.

## Set v5 (üretim tarifi, üretimden önce sabitlendi)
- Üreteç: `scripts/generate_holdout_v2.py` ile
  `manifest.json RW-HLD5 5001 frozen_holdout_v5 20261102 manifest_v4_eval.json`
- 20 senaryo, RW-HLD5-001…020, tohumlar 5001…, tarif v2 dağılımıyla aynı.
- Üretimden sonra set dondurulur; aday üzerinde hiçbir değişiklik yapılmaz.

## Başarı ölçütü
Beş kapının tamamı: Gate1 baseline FAIL tekrarı, Gate2 eşleştirilmiş
karşılaştırma, Gate3 v5'te 20/20, Gate4 regresyonlar, Gate5 mühür bütünlüğü.
Sonuç ne çıkarsa (VERIFIED ya da REJECTED) aynen raporlanacak; tutmazsa yeni
set üretilip tekrar denenmeyecek (bu, set alışverişi olurdu).

## SONUÇ (2026-11-02, ölçüldü)
- Doğrulama `verif-ec5ae352765d`: **REJECTED**. Gate 1, 2, 4, 5 PASS;
  Gate 3: **18/20**. Başarısızlar:
  - RW-HLD5-008: MIN_CLEARANCE_VIOLATION + STUCK + TIMEOUT + GOAL_NOT_REACHED
    (en düşük mesafe 0.1156 m)
  - RW-HLD5-016: STUCK (hedefe ulaşmasına rağmen; yavaş sürünme takılma
    sayılmış)
- Aşırı temkinli aday da beklendiği gibi REJECTED (`verif-f810a98959e2`).
- Path B hâlâ AÇIK: beşinci taze sette de 18/20. Ön kayda uyuldu — yeni set
  üretilip tekrar denenmeyecek. Bir sonraki adım set değil, kontrolcü
  ailesini zenginleştirmek (özellikle takılma önleme) ve ancak o zaman yeni
  bir ön kayıt + taze set (v6) ile tek atış yapmaktır.
