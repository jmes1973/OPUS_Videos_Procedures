from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os

from PIL import Image
import pytesseract

RUTA_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(RUTA_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = RUTA_TESSERACT


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def normalizar_texto(texto: str) -> str:
    return " ".join(texto.strip().split())


def inferir_region_global() -> str:
    return "global"


def leer_texto_imagen(
    image_path: str | Path,
    idioma_ocr: str = "eng",
    confianza_minima: float = 30.0
) -> dict[str, Any]:
    image_path = Path(image_path)

    with Image.open(image_path) as img:
        data = pytesseract.image_to_data(
            img,
            lang=idioma_ocr,
            output_type=pytesseract.Output.DICT
        )

    textos_visibles: list[dict[str, Any]] = []
    confianzas_validas: list[float] = []

    total_items = len(data["text"])

    for i in range(total_items):
        texto = normalizar_texto(data["text"][i])
        conf = data["conf"][i]

        try:
            conf = float(conf)
        except Exception:
            conf = -1.0

        if not texto:
            continue

        if conf < confianza_minima:
            continue

        textos_visibles.append({
            "texto": texto,
            "confianza": round(conf / 100.0, 4),
            "region": inferir_region_global()
        })

        confianzas_validas.append(conf / 100.0)

    ocr_calidad_global = round(
        sum(confianzas_validas) / len(confianzas_validas),
        4
    ) if confianzas_validas else 0.0

    return {
        "image_path": str(image_path).replace("\\", "/"),
        "textos_visibles": textos_visibles,
        "ocr_calidad_global": ocr_calidad_global
    }


def construir_ocr_observations_desde_frames_index(
    frames_index: dict[str, Any],
    idioma_ocr: str = "eng",
    confianza_minima: float = 30.0
) -> dict[str, Any]:
    frames = frames_index.get("frames", [])

    observations: list[dict[str, Any]] = []

    for frame in frames:
        image_path = frame.get("image_path", "")
        if not image_path:
            continue

        ocr_result = leer_texto_imagen(
            image_path=image_path,
            idioma_ocr=idioma_ocr,
            confianza_minima=confianza_minima
        )

        observations.append({
            "frame_id": frame.get("frame_id", ""),
            "timestamp": frame.get("timestamp", ""),
            "timestamp_seconds": frame.get("timestamp_seconds", 0.0),
            "image_path": ocr_result["image_path"],
            "textos_visibles": ocr_result["textos_visibles"],
            "ocr_calidad_global": ocr_result["ocr_calidad_global"]
        })

    return {
        "video_id": frames_index.get("video_id", ""),
        "run_id": frames_index.get("run_id", ""),
        "source_video": frames_index.get("source_video", ""),
        "ocr_config": {
            "idioma_ocr": idioma_ocr,
            "confianza_minima": confianza_minima
        },
        "observations": observations
    }


def crear_ocr_observations_desde_frames_index(
    frames_index_path: str | Path,
    output_path: str | Path,
    idioma_ocr: str = "eng",
    confianza_minima: float = 30.0
) -> dict[str, Any]:
    frames_index = cargar_json(frames_index_path)

    resultado = construir_ocr_observations_desde_frames_index(
        frames_index=frames_index,
        idioma_ocr=idioma_ocr,
        confianza_minima=confianza_minima
    )

    guardar_json(output_path, resultado)
    return resultado
