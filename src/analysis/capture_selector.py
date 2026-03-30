from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def indexar_frames_por_id(frames_index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frames = frames_index.get("frames", [])
    return {frame["frame_id"]: frame for frame in frames if "frame_id" in frame}


def seleccionar_mejor_frame_para_paso(
    step: dict[str, Any],
    frames_por_id: dict[str, dict[str, Any]]
) -> tuple[str, str, str, str, float, bool, str]:
    primary_frame_id = step.get("primary_frame", "")

    if primary_frame_id and primary_frame_id in frames_por_id:
        frame = frames_por_id[primary_frame_id]
        return (
            primary_frame_id,
            "primary_frame",
            frame.get("image_path", ""),
            frame.get("timestamp", ""),
            float(frame.get("timestamp_seconds", 0.0)),
            False,
            ""
        )

    start_seconds = float(step.get("start_seconds", 0.0))
    end_seconds = float(step.get("end_seconds", 0.0))

    candidatos: list[dict[str, Any]] = []
    for frame in frames_por_id.values():
        ts = float(frame.get("timestamp_seconds", 0.0))
        if start_seconds <= ts <= end_seconds:
            candidatos.append(frame)

    candidatos.sort(
        key=lambda f: (
            not bool(f.get("is_candidate", False)),
            not bool(f.get("is_keyframe", False)),
            -float(f.get("change_score_prev", 0.0))
        )
    )

    if candidatos:
        frame = candidatos[0]
        return (
            frame.get("frame_id", ""),
            "fallback_frame",
            frame.get("image_path", ""),
            frame.get("timestamp", ""),
            float(frame.get("timestamp_seconds", 0.0)),
            True,
            "No se encontró primary_frame; se usó un frame alternativo dentro del rango temporal del paso."
        )

    return (
        "",
        "sin_frame",
        "",
        "",
        0.0,
        True,
        "No se encontró ningún frame adecuado para ilustrar el paso."
    )


def construir_capture_plan(
    steps_normalized: dict[str, Any],
    frames_index: dict[str, Any]
) -> dict[str, Any]:
    steps = steps_normalized.get("steps", [])
    frames_por_id = indexar_frames_por_id(frames_index)

    captures: list[dict[str, Any]] = []
    contador = 1

    for step in steps:
        selected_frame_id, selection_type, image_path, timestamp, timestamp_seconds, requires_manual_review, review_reason = seleccionar_mejor_frame_para_paso(
            step,
            frames_por_id
        )

        if selection_type == "primary_frame":
            selection_reason = "Se utiliza el frame principal asociado al paso."
        elif selection_type == "fallback_frame":
            selection_reason = "Se utiliza un frame alternativo dentro del rango temporal del paso."
        else:
            selection_reason = "No fue posible seleccionar automáticamente una captura válida."

        capture = {
            "capture_id": f"cap_{contador:04d}",
            "step_id": step.get("step_id", ""),
            "step_order": step.get("step_order", 0),
            "selected_frame_id": selected_frame_id,
            "selection_type": selection_type,
            "image_path": image_path,
            "timestamp": timestamp,
            "timestamp_seconds": timestamp_seconds,
            "selection_reason": selection_reason,
            "requires_manual_review": requires_manual_review,
            "review_reason": review_reason,
            "technical_notes": step.get("title", "")
        }

        captures.append(capture)
        contador += 1

    resumen = {
        "total_captures": len(captures),
        "captures_with_primary_frame": sum(1 for c in captures if c["selection_type"] == "primary_frame"),
        "captures_with_fallback_frame": sum(1 for c in captures if c["selection_type"] == "fallback_frame"),
        "captures_requiring_manual_review": sum(1 for c in captures if c["requires_manual_review"])
    }

    return {
        "video_id": steps_normalized.get("video_id", ""),
        "run_id": steps_normalized.get("run_id", ""),
        "source_video": steps_normalized.get("source_video", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "capture_selection_config": {
            "source_steps_normalized": "",
            "source_frames_index": "",
            "prefer_primary_frame": True,
            "allow_fallback_frame": True,
            "minimum_image_width": 0
        },
        "summary": resumen,
        "captures": captures
    }


def crear_capture_plan_desde_steps(
    steps_normalized_path: str | Path,
    frames_index_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    steps_normalized = cargar_json(steps_normalized_path)
    frames_index = cargar_json(frames_index_path)

    resultado = construir_capture_plan(
        steps_normalized=steps_normalized,
        frames_index=frames_index
    )

    resultado["capture_selection_config"]["source_steps_normalized"] = str(steps_normalized_path)
    resultado["capture_selection_config"]["source_frames_index"] = str(frames_index_path)

    guardar_json(output_path, resultado)
    return resultado
