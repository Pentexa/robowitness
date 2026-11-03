"use client";

import React, { useEffect, useRef, useState } from "react";
import { Camera, Upload } from "lucide-react";
import {
  detectImage, fetchSavedImageScenarios, previewImageScenario,
  type ImageDetectionResult, type ImageScenarioResult,
} from "../lib/api";
import { useLocale } from "../lib/i18n";
import { ScenarioSpec } from "../lib/types";

interface Props {
  disabled: boolean;
  active: boolean;
  onScenario: (scenario: ScenarioSpec, runNow: boolean) => Promise<void>;
}

export function ImageScenarioPanel({ disabled, active, onScenario }: Props) {
  const { locale } = useLocale();
  const text = (en: string, tr: string) => locale === "tr" ? tr : en;
  const [image, setImage] = useState<string | null>(null);
  const [concepts, setConcepts] = useState("object");
  const [detections, setDetections] = useState<ImageDetectionResult | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [name, setName] = useState("Image scenario");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [overhead, setOverhead] = useState(false);
  const [start, setStart] = useState({ x: 0.1, y: 0.5 });
  const [goal, setGoal] = useState({ x: 0.9, y: 0.5 });
  const [placing, setPlacing] = useState<"start" | "goal">("start");
  const [preview, setPreview] = useState<ImageScenarioResult | null>(null);
  const [saved, setSaved] = useState<ImageScenarioResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraRequest = useRef(0);

  const stopCamera = () => {
    cameraRequest.current += 1;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraActive(false);
  };

  useEffect(() => {
    fetchSavedImageScenarios().then(setSaved).catch(() => undefined);
    return () => {
      cameraRequest.current += 1;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (cameraActive && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => setError("Camera preview could not start"));
    }
  }, [cameraActive]);

  useEffect(() => {
    setPreview(null);
    setNotice(null);
  }, [width, height, overhead, start, goal, selected, name]);

  useEffect(() => {
    if (disabled || !active) {
      cameraRequest.current += 1;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraActive(false);
    }
  }, [disabled, active]);

  const acceptImage = (dataUrl: string) => {
    stopCamera();
    setImage(dataUrl);
    setDetections(null);
    setSelected([]);
    setPreview(null);
    setError(null);
    setNotice(null);
  };

  const upload = async (file?: File) => {
    if (!file) return;
    setError(null);
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 5_000_000) {
      setError(text("Choose a PNG, JPEG or WebP photo up to 5 MB.", "En fazla 5 MB PNG, JPEG veya WebP fotoğraf seçin."));
      return;
    }
    setBusy(true);
    try {
      // Normalize EXIF orientation and size before both preview and inference.
      const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      acceptImage(canvas.toDataURL("image/jpeg", 0.92));
    } catch {
      setError(text("This photo could not be decoded.", "Fotoğraf okunamadı."));
    } finally { setBusy(false); }
  };

  const openCamera = async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(text("Camera requires localhost or HTTPS and a supported browser.", "Kamera için localhost veya HTTPS ve desteklenen tarayıcı gerekir."));
      return;
    }
    stopCamera();
    const request = ++cameraRequest.current;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1600 }, height: { ideal: 1200 } }, audio: false,
      });
      if (request !== cameraRequest.current) { stream.getTracks().forEach((t) => t.stop()); return; }
      streamRef.current = stream;
      setCameraActive(true);
    } catch {
      setError(text("Camera access failed. Allow camera permission or upload a photo.", "Kamera açılamadı. Kamera izni verin veya fotoğraf yükleyin."));
    }
  };

  const capture = () => {
    const video = videoRef.current;
    if (!video?.videoWidth) return;
    const scale = Math.min(1, 1600 / Math.max(video.videoWidth, video.videoHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d")!.drawImage(video, 0, 0, canvas.width, canvas.height);
    acceptImage(canvas.toDataURL("image/jpeg", 0.92));
  };

  const detect = async () => {
    if (!image) return;
    setBusy(true); setError(null); setPreview(null); setNotice(null);
    setDetections(null);
    setSelected([]);
    try {
      const result = await detectImage(image, concepts.split(/\r?\n/).map((v) => v.trim()).filter(Boolean));
      setDetections(result);
      // Select nothing when there are too many, so no objects are silently dropped.
      setSelected(result.detections.length <= 8 ? result.detections.map((d) => d.id) : []);
    } catch (e) { setError(e instanceof Error ? e.message : "SAM request failed"); }
    finally { setBusy(false); }
  };

  const convert = async (save: boolean, runNow = false) => {
    if (!detections) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const result = await previewImageScenario({
        detection_id: detections.detection_id, selected_ids: selected, name,
        width_m: Number(width), height_m: Number(height), overhead_confirmed: true,
        start, goal, save,
      });
      setPreview(result);
      if (save) {
        // Save is confirmed by the server; a separate history refresh must
        // not prevent the requested simulation from starting.
        setSaved((prev) => [result, ...prev.filter((item) => item.scenario.id !== result.scenario.id)].slice(0, 100));
        setNotice(text("Scenario saved.", "Senaryo kaydedildi."));
        await onScenario(result.scenario, runNow);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Scenario conversion failed"); }
    finally { setBusy(false); }
  };

  const locked = busy || disabled;
  return (
    <section className="rw-section">
      <details id="image-scenario-panel" onToggle={(e) => { if (!e.currentTarget.open) stopCamera(); }}>
        <summary className="rw-section-title">{text("Camera / Photo → SAM 3.1", "Kamera / Fotoğraf → SAM 3.1")}</summary>
        <div className="rw-image-form">
          <p className="rw-summary">{text("A still photo is sent to Meta when you click Detect. Enter the real floor dimensions to build a simulation.", "Tespit Et düğmesiyle fotoğraf Meta'ya gönderilir. Simülasyon için gerçek zemin ölçülerini girin.")}</p>
          <fieldset disabled={locked} className="rw-image-fields">
            <div className="rw-btn-row">
              <label className="rw-btn rw-btn-ghost rw-btn-sm">
                <Upload size={14} /> {text("Upload photo", "Fotoğraf yükle")}
                <input id="input-scenario-photo" type="file" accept="image/png,image/jpeg,image/webp" aria-label={text("Upload photo", "Fotoğraf yükle")} onChange={(e) => { void upload(e.target.files?.[0]); e.target.value = ""; }} />
              </label>
              <button id="btn-open-camera" className="rw-btn rw-btn-ghost rw-btn-sm" onClick={openCamera}><Camera size={14} />{text("Open camera", "Kamerayı aç")}</button>
            </div>
            {cameraActive && <div>
              <video ref={videoRef} muted playsInline className="rw-photo" aria-label={text("Camera preview", "Kamera önizlemesi")} />
              <div className="rw-btn-row">
                <button id="btn-capture-photo" className="rw-btn" onClick={capture}>{text("Capture photo", "Fotoğraf çek")}</button>
                <button className="rw-btn" onClick={stopCamera}>{text("Close camera", "Kamerayı kapat")}</button>
              </div>
            </div>}
            {image && <>
              <svg id="image-detection-preview" viewBox="0 0 1000 700" className="rw-photo" aria-label={text("Photo and detected objects", "Fotoğraf ve tespit edilen nesneler")} onClick={(e) => {
                if (!detections || locked) return;
                // The SVG can have letterboxing under max-height on laptops.
                // Invert its actual transform instead of scaling the element box.
                const transform = e.currentTarget.getScreenCTM();
                if (!transform) return;
                const pixel = new DOMPoint(e.clientX, e.clientY).matrixTransform(transform.inverse());
                const point = { x: pixel.x / 1000, y: pixel.y / 700 };
                if (point.x < 0 || point.x > 1 || point.y < 0 || point.y > 1) return;
                if (placing === "start") setStart(point); else setGoal(point);
              }}>
                <image href={image} width="1000" height="700" preserveAspectRatio="none" />
                {detections?.detections.map((d, i) => <g key={d.id}>
                  <rect x={d.box.left / detections.image_width * 1000} y={d.box.top / detections.image_height * 700} width={(d.box.right - d.box.left) / detections.image_width * 1000} height={(d.box.bottom - d.box.top) / detections.image_height * 700} fill="none" stroke={selected.includes(d.id) ? "#ef4444" : "#888"} strokeWidth="4" />
                  <text x={d.box.left / detections.image_width * 1000} y={d.box.top / detections.image_height * 700 - 6} fontSize="28" fill="#dc2626">{i + 1}</text>
                </g>)}
                {detections && <>
                  <circle cx={start.x * 1000} cy={start.y * 700} r="16" fill="#2563eb" /><text x={start.x * 1000 + 20} y={start.y * 700} fontSize="28" fill="#2563eb">S</text>
                  <circle cx={goal.x * 1000} cy={goal.y * 700} r="16" fill="#15803d" /><text x={goal.x * 1000 + 20} y={goal.y * 700} fontSize="28" fill="#15803d">G</text>
                </>}
              </svg>
              <label className="rw-field">{text("Object types (one concept per line, maximum 3)", "Nesne türleri (satır başına tek kavram, en fazla 3)")}
                <textarea id="input-sam-concepts" className="rw-input" rows={3} value={concepts} onChange={(e) => setConcepts(e.target.value)} placeholder={"chair\nbox\nperson"} />
              </label>
              <button id="btn-detect-photo" className="rw-btn rw-btn-primary" onClick={detect}>{text("Detect with SAM 3.1", "SAM 3.1 ile Tespit Et")}</button>
            </>}
            {detections && <>
              <p className="rw-summary" role="status">LIVE_META · sam-3.1 · {detections.detections.length} {text("objects detected", "nesne tespit edildi")}</p>
              {!detections.detections.length && <p className="rw-summary">{text("No matches. Name a concrete object visible in the photo and try again.", "Eşleşme yok. Fotoğrafta görülen somut bir nesneyi yazıp tekrar deneyin.")}</p>}
              {detections.detections.map((d, i) => <label key={d.id} className="rw-image-check">
                <input type="checkbox" checked={selected.includes(d.id)} disabled={!selected.includes(d.id) && selected.length >= 8} onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, d.id] : prev.filter((id) => id !== d.id))} />
                {i + 1}. {d.concept} {d.confidence !== null ? `(${Math.round(d.confidence * 100)}%)` : ""}
              </label>)}
              <p className="rw-summary">{text("Select 1–8 obstacles. Use an overhead or rectified view of the entire rectangular floor. Perspective photos need rectification first; scale alone does not recover depth.", "1–8 engel seçin. Dikdörtgen zeminin tamamını üstten gösteren veya düzeltilmiş görüntü kullanın. Perspektif fotoğraf önce düzeltilmelidir; ölçek tek başına derinliği vermez.")}</p>
              <label className="rw-field">{text("Scenario name", "Senaryo adı")}<input id="input-image-name" className="rw-input" value={name} onChange={(e) => setName(e.target.value)} maxLength={120} /></label>
              <div className="rw-btn-row">
                <label className="rw-field">{text("Floor width (m)", "Zemin genişliği (m)")}<input id="input-image-width" className="rw-input" type="number" min="6" max="20" step="0.1" value={width} onChange={(e) => setWidth(e.target.value)} /></label>
                <label className="rw-field">{text("Floor height (m)", "Zemin yüksekliği (m)")}<input id="input-image-height" className="rw-input" type="number" min="4" max="15" step="0.1" value={height} onChange={(e) => setHeight(e.target.value)} /></label>
              </div>
              <label className="rw-image-check"><input id="check-image-overhead" type="checkbox" checked={overhead} onChange={(e) => setOverhead(e.target.checked)} />{text("I confirm this is an overhead / rectified floor view.", "Bunun üstten / düzeltilmiş zemin görüntüsü olduğunu onaylıyorum.")}</label>
              <div className="rw-btn-row">
                <button className="rw-btn rw-btn-sm" aria-pressed={placing === "start"} onClick={() => setPlacing("start")}>{text("Place start (S)", "Başlangıcı yerleştir (S)")}</button>
                <button className="rw-btn rw-btn-sm" aria-pressed={placing === "goal"} onClick={() => setPlacing("goal")}>{text("Place goal (G)", "Hedefi yerleştir (G)")}</button>
              </div>
              <p className="rw-summary">{text("Click the photo to place the selected point, or enter image coordinates (%).", "Seçili noktayı fotoğrafa tıklayarak yerleştirin veya görüntü koordinatlarını (%) girin.")}</p>
              <div className="rw-image-points">{(["start", "goal"] as const).map((kind) => <React.Fragment key={kind}>{(["x", "y"] as const).map((axis) => <label className="rw-field" key={axis}>{kind === "start" ? "S" : "G"} {axis.toUpperCase()} %
                <input id={`input-image-${kind}-${axis}`} className="rw-input" type="number" min="0" max="100" step="1" value={Math.round((kind === "start" ? start : goal)[axis] * 100)} onChange={(e) => (kind === "start" ? setStart : setGoal)((prev) => ({ ...prev, [axis]: Number(e.target.value) / 100 }))} />
              </label>)}</React.Fragment>)}</div>
              <button id="btn-preview-image-scenario" className="rw-btn rw-btn-primary" disabled={!overhead || !width || !height || selected.length === 0} onClick={() => convert(false)}>{text("Preview scenario", "Senaryoyu önizle")}</button>
            </>}
            {preview && <div id="image-scenario-result">
              <p className="rw-summary">{preview.scenario.world.width_m} × {preview.scenario.world.height_m} m · {preview.scenario.obstacles.length} {text("static obstacles", "sabit engel")}</p>
              <svg viewBox={`0 0 ${preview.scenario.world.width_m} ${preview.scenario.world.height_m}`} className="rw-photo" aria-label={text("Simulation scenario preview", "Simülasyon senaryosu önizlemesi")}>
                <rect width={preview.scenario.world.width_m} height={preview.scenario.world.height_m} fill="#fafafa" stroke="#777" strokeWidth="0.05" />
                {preview.scenario.obstacles.map((o) => <circle key={o.id} cx={o.start.x_m} cy={preview.scenario.world.height_m - o.start.y_m} r={o.radius_m} fill="#777" />)}
                <circle cx={preview.scenario.robot.start.x_m} cy={preview.scenario.world.height_m - preview.scenario.robot.start.y_m} r="0.25" fill="#2563eb" />
                <circle cx={preview.scenario.robot.goal.x_m} cy={preview.scenario.world.height_m - preview.scenario.robot.goal.y_m} r="0.35" fill="#15803d" />
              </svg>
              <p className="rw-summary">{text("Boxes are enclosed by static circles. Hidden objects and motion are unknown. Review the approximation before saving.", "Kutular sabit dairelerle çevrelenir. Gizli nesneler ve hareket bilinmez. Kaydetmeden önce yaklaşımı inceleyin.")}</p>
              {preview.warnings.length > 1 && <p className="rw-summary">{preview.warnings.slice(1).join(" ")}</p>}
              <div className="rw-btn-row">
                <button id="btn-save-image-scenario" className="rw-btn" onClick={() => convert(true)}>{text("Save and use", "Kaydet ve kullan")}</button>
                <button id="btn-run-image-scenario" className="rw-btn rw-btn-primary" onClick={() => convert(true, true)}>{text("Save and run", "Kaydet ve çalıştır")}</button>
              </div>
            </div>}
            {saved.length > 0 && <label className="rw-field">{text("Saved image scenarios", "Kayıtlı görüntü senaryoları")}
              <select id="select-saved-image-scenario" className="rw-input" value="" onChange={(e) => { const s = saved.find((item) => item.scenario.id === e.target.value); if (s) void onScenario(s.scenario, false); }}>
                <option value="">{text("Select a saved scenario", "Kayıtlı senaryo seçin")}</option>
                {saved.map((s) => <option key={s.scenario.id} value={s.scenario.id}>{s.name}</option>)}
              </select>
            </label>}
          </fieldset>
          {busy && <p role="status" className="rw-summary">{text("Processing…", "İşleniyor…")}</p>}
          {error && <p role="alert" className="rw-err">{error}</p>}
          {notice && <p role="status" className="rw-summary">{notice}</p>}
        </div>
      </details>
    </section>
  );
}
