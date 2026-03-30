from __future__ import annotations

from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any
import json


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def calcular_hash_texto(texto: str) -> str:
    return sha1(texto.encode("utf-8")).hexdigest()[:12]


def normalizar_marca_visual(marca: str, marcas_permitidas: list[str]) -> str | None:
    if not marca:
        return None

    marca_limpia = marca.strip().lower()

    if marca_limpia in marcas_permitidas:
        return marca_limpia

    equivalencias = {
        "cursor_visible": "cursor_presente",
        "menu_desplegable_visible": "desplegable_visible",
        "panel_flotante_visible": "panel_visible",
        "texto_visible_superpuesto": "texto_superpuesto_visible",
        "cambio_ui_visible": "cambio_interfaz_visible",
        "slider_visible": "control_deslizante_visible",
        "dialogo_visible": "dialogo_visible",
        "icono_visible": "icono_visible",
        "indicador_visible": "indicador_visible"
    }

    marca_normalizada = equivalencias.get(marca_limpia)
    if marca_normalizada in marcas_permitidas:
        return marca_normalizada

    return None


def normalizar_marcas_visuales(
    marcas: list[str] | None,
    marcas_permitidas: list[str]
) -> list[str]:
    if not marcas:
        return []

    resultado: list[str] = []
    for marca in marcas:
        marca_normalizada = normalizar_marca_visual(marca, marcas_permitidas)
        if marca_normalizada and marca_normalizada not in resultado:
            resultado.append(marca_normalizada)

    return resultado


def construir_timestamp_hms(segundos: float) -> str:
    if segundos < 0:
        raise ValueError("timestamp_seconds no puede ser negativo")

    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segundos_enteros = int(segundos % 60)
    milisegundos = int(round((segundos - int(segundos)) * 1000))

    if milisegundos == 1000:
        segundos_enteros += 1
        milisegundos = 0

    return f"{horas:02d}:{minutos:02d}:{segundos_enteros:02d}.{milisegundos:03d}"


def validar_frame_entrada(frame: dict[str, Any]) -> None:
    campos_obligatorios = [
        "frame_id",
        "timestamp_seconds",
        "image_path"
    ]

    faltantes = [campo for campo in campos_obligatorios if campo not in frame]
    if faltantes:
        raise ValueError(f"Frame inválido. Faltan campos obligatorios: {faltantes}")

    if not isinstance(frame["timestamp_seconds"], (int, float)):
        raise TypeError("timestamp_seconds debe ser numérico")

    if frame["timestamp_seconds"] < 0:
        raise ValueError("timestamp_seconds no puede ser negativo")


def construir_frames_index(
    video_id: str,
    run_id: str,
    source_video: str,
    frames_metadata: list[dict[str, Any]],
    terminology_path: str | Path,
    extraction_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not video_id.strip():
        raise ValueError("video_id no puede estar vacío")
    if not run_id.strip():
        raise ValueError("run_id no puede estar vacío")
    if not source_video.strip():
        raise ValueError("source_video no puede estar vacío")

    terminology = cargar_json(terminology_path)
    marcas_permitidas = terminology.get("marcas_visuales_permitidas", [])

    frames_salida: list[dict[str, Any]] = []
    change_scores: list[float] = []
    total_keyframes = 0
    total_candidate_frames = 0

    total_frames = len(frames_metadata)

    for indice, frame in enumerate(frames_metadata):
        validar_frame_entrada(frame)

        timestamp_seconds = float(frame["timestamp_seconds"])
        timestamp = frame.get("timestamp") or construir_timestamp_hms(timestamp_seconds)

        image_path = str(frame["image_path"])
        image_hash = frame.get("image_hash") or calcular_hash_texto(image_path)

        is_keyframe = bool(frame.get("is_keyframe", False))
        is_candidate = bool(frame.get("is_candidate", False))
        change_score_prev = float(frame.get("change_score_prev", 0.0))
        change_score_next = float(frame.get("change_score_next", 0.0))

        visual_flags = normalizar_marcas_visuales(
            frame.get("visual_flags", []),
            marcas_permitidas
        )

        frame_salida = {
            "frame_id": str(frame["frame_id"]),
            "frame_number_source": frame.get("frame_number_source", None),
            "timestamp": timestamp,
            "timestamp_seconds": timestamp_seconds,
            "relative_position": round(indice / max(total_frames - 1, 1), 4),
            "image_path": image_path,
            "image_hash": image_hash,
            "width": int(frame.get("width", 0)),
            "height": int(frame.get("height", 0)),
            "extraction_type": str(frame.get("extraction_type", "uniform")),
            "is_keyframe": is_keyframe,
            "is_candidate": is_candidate,
            "change_score_prev": change_score_prev,
            "change_score_next": change_score_next,
            "duplicate_group": frame.get("duplicate_group", None),
            "visual_flags": visual_flags,
            "technical_notes": str(frame.get("technical_notes", ""))
        }

        frames_salida.append(frame_salida)
        change_scores.append(change_score_prev)

        if is_keyframe:
            total_keyframes += 1
        if is_candidate:
            total_candidate_frames += 1

    average_change_score = round(sum(change_scores) / len(change_scores), 4) if change_scores else 0.0
    max_change_score = round(max(change_scores), 4) if change_scores else 0.0
    video_duration_seconds = round(
        max((frame["timestamp_seconds"] for frame in frames_salida), default=0.0),
        4
    )

    return {
        "video_id": video_id,
        "run_id": run_id,
        "source_video": source_video,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "extraction_config": extraction_config or {
            "mode": "uniform",
            "target_fps": 1,
            "keyframe_detection": False,
            "diff_method": "ninguno",
            "diff_threshold": 0.0,
            "save_format": "jpg"
        },
        "summary": {
            "total_frames_indexed": len(frames_salida),
            "total_keyframes": total_keyframes,
            "total_candidate_frames": total_candidate_frames,
            "video_duration_seconds": video_duration_seconds,
            "average_change_score": average_change_score,
            "max_change_score": max_change_score
        },
        "frames": frames_salida
    }


def crear_frames_index_desde_metadata(
    video_id: str,
    run_id: str,
    source_video: str,
    frames_metadata_path: str | Path,
    terminology_path: str | Path,
    output_path: str | Path,
    extraction_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    frames_metadata = cargar_json(frames_metadata_path)
    if not isinstance(frames_metadata, list):
        raise TypeError("El archivo de metadatos de frames debe contener una lista")

    resultado = construir_frames_index(
        video_id=video_id,
        run_id=run_id,
        source_video=source_video,
        frames_metadata=frames_metadata,
        terminology_path=terminology_path,
        extraction_config=extraction_config
    )

    guardar_json(output_path, resultado)
    return resultado

