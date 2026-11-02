# RoboWitness 90 Sn — AI Video Sahne Promptları

> Araçlar: Runway Gen-4 / Kling / Veo / Pika / Hailuo (10 s üstü klipler, 16:9).
> Akış önerisi: **stills-first** — her sahiyi önce Flux/Midjourney'de sabit kare olarak
> üret, sonra "image-to-video" ile canlandır. Style kelime seti kliplerde SABİT kalsın;
> seed'i kilitliysen klipleri birbirine benzetir.

---

## Ortak Stil Bloğu (her promptu sonuna ekle)

```text
STYLE: dark tech documentary aesthetic, near-black background #0d1117, thin cyan
wireframe grid, glowing red and green accents, volumetric haze, shallow depth of
field, macro detail, cinematic 24fps, heavy negative space, no text, no watermark,
no brand logos, no people, no faces
```

**Görüntüleyici negatif prompt (kullandığı aracının desteklerse):**

```text
text, letters, numbers, captions, watermark, logo, human face, hands, cartoon,
bright daylight, cluttered background, extra limbs, morphing objects
```

**Dürüstlük notu:** AI klipler konsept B-roll'dur. S1 ve S2 kliplerinin köşesine küçük
etiket: `konsept görsel · gerçek arayüz simülasyonda`. Ürünün güvenilirliği gerçek
ekran kayıtlarından gelir.

---

## S1 — Hook: Çarpışma (0:00–0:06)

**S1A · Top-down koridor yaklaşımı** (~5 sn)

```text
Top-down aerial view of a minimalist dark warehouse floor with a thin cyan grid,
a small rounded autonomous delivery robot (plain, no logos) rolls fast down one
long corridor toward a plain wall, the grid flashes deep red the instant it gets
within centimeters of the wall, camera slowly pushes in, volumetric haze,
+ [STIL BLOĞU]
```

**S1B · Makro temas anı** (slow-mo katman, ~2 sn)

```text
Extreme macro slow motion: the dark metallic bumper of a small robot touching a
flat wall, at the moment of contact a red light wave ripples across both surfaces
like a shockwave, freeze-frame feel, black void background,
+ [STIL BLOĞU]
```

**Kurgu:** S1A'yı 0.5× yavaşlat; temas karesinde yeşil üstüne kırmızı flaş; "Tick 358"
sarcadır kurguda.

## S2 — Sorun: Kendini puanlama (0:06–0:16)

**S2A · Mührü vuran kol** (~6 sn)

```text
A single glowing document floats in dark empty space; a small robotic stamp arm
hovers above it and presses down one round wax seal; the seal's glow shifts from
calm green to warning red right after it lands, dramatic rim light, macro, black
void background, the stamp face is completely blank,
+ [STIL BLOĞU]
```

**S2B (opsiyonel) · Ayna yalanı** (~4 sn)

```text
In black space, a translucent hologram robot arm draws a glowing check mark in the
air; immediately the same check mark distorts and consumes itself in red static,
minimalist, negative space at bottom third for caption,
+ [STIL BLOĞU]
```

**Kurgu:** mühür yüzesine "ONAYLANDI" ve kırmızı sürümlerine "İNTERNET YOK" değil —
kendi ekstremi: "KENDİSİ ONAYLADI" yagısı ekle.

## S3 — Mimari: 4 rol (0:16–0:34)

**S3A · Dört düğüm zinciri** (~8 sn)

```text
Abstract dataflow in deep dark space: a single pulse of orange light travels left
to right through four floating geometric nodes, each node wakes up and locks in
place as the pulse arrives, thin wireframe links connect the nodes, slow lateral
dolly camera, negative space above and below the nodes for labels,
+ [STIL BLOĞU]
```

**S3B · Gözlem dürüstlüğü** (~6 sn)

```text
Top-down blueprint view of a wireframe mobile robot in a sparse obstacle field
rendered as a clean 3D point cloud, a red danger ring pulses around the nearest
obstacle, a faint cyan ghost echo of the robot trails behind it to suggest sensor
delay, elegant minimal motion, no text,
+ [STIL BLOĞU]
```

**Kurgu:** düğümlerin sırası=PROPOSER → SIMULATOR (60 Hz) → ORACLE → EVIDENCE
etiketleri, kurguda.

## S4 — Beş red montajı (0:34–1:00) — dram merkezi

**S4A · Tek plan yol (denemekte önerilen)** (~8 sn)

```text
Slow lateral dolly past a row of five identical dark monolith slabs standing in a
black void, as the camera passes each slab its thin edge glow flickers red and
dies out one by one, dust motes in the light, no text,
+ [STIL BLOĞU]
```

**S4B · Fallback: 5 ayrı kısa klip** (her biri ~2 sn, farklı seed)

```text
One dark monolith slab in a black void, its edge glow suddenly flashes bright red
and the light collapses into darkness,
+ [STIL BLOĞU]
```

**Kurgu:** her kırmızı sönüşte üstüne `V2 17/20 ❌` … `V6 18/20 ❌` satırını binary
olarak ekleyin; beşinci sönüşten sonra 1 sn tam sessizlik.

## S5 — Tek şans: Ön kayıt → 20/20 (1:00–1:20)

**S5A · Mühür (kayıt)** (~4 sn)

```text
A dark evidence folder in black space gets wrapped by a glowing seal wire; a blank
wax stamp presses down and locks with a small light burst, macro, no text,
+ [STIL BLOĞU]
```

**S5B · 20 karo sıraya yeşil** (~6 sn)

```text
A flat grid of twenty square glass tiles floats in dark space; a green light
sweeps across the grid and tiles ignite with steady green glow in sequence until
the whole grid is lit, calm confident motion, no text,
+ [STIL BLOĞU]
```

**S5C · Kapı mührü doğrulama** (~4 sn)

```text
A sealed dark vault box in deep space, a clean green scanning laser line runs
top to bottom over its surface and the surface lights up sleek and untouched,
volumetric haze, no text,
+ [STIL BLOĞU]
```

**Kurgu:** S5B bitiminde 20/20 üstüne büyük yazı: `20/20 · VERIFIED_IN_SIMULATION`.

## S6 — Terminal (1:20–1:24)

**AI ile ÜRETME.** `verify_evidence.py` gerçek çıktısı mutlaka gerçek kayıt.
Arka plan derinliği istersen AI katmanı:

```text
Very dark shallow-focus bokeh of distant blinking server LEDs in a black void,
barely visible, no text,
+ [STIL BLOĞU]
```

## S7 — Kapanış (1:24–1:30)

**S7 · Soluk çözülme + logo boşluğu** (~6 sn)

```text
In a near-black void a single soft green pulse expands gently into a warm dim
gradient, dust motes drift, camera pulls back slowly, big empty negative space
center-frame for a logo to appear, no text,
+ [STIL BLOĞU]
```

## Ekstra — Thumbnail / kapak karesi

```text
A tiny rounded autonomous robot alone in a vast dark wireframe warehouse seen top
down, a single distant gate of green light glows far ahead of it, lonely
cinematic composition, no text,
+ [STIL BLOĞU]
```

---

## Üretim sırası (öneri)

1. Stills: yukarıdaki her promptu önce Flux/Midjourney'de sabit kare üret (en az 3 varyant).
2. Image-to-video: onayladığın kareyi Runway/Kling'e ver; motion'un %10–30 aralığını
   aşırı kullanma — az hareket = az moru offence.
3. Text-free olmayı kontrol et: yazı sızdıysa tekrar üret.
4. Kurgu: AI klipleri "katman" olarak; gerçek ürün kayıtlarını %60+ ekranda tut.
