from __future__ import annotations

from datetime import datetime
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


def extraer_titulos_normalizados(terminology: dict[str, Any]) -> set[str]:
    return set(terminology.get("titulos_pasos_normalizados", []))


def inferir_titulo_y_instruccion(
    sequence_label: str,
    sequence_summary: str,
    titulos_permitidos: set[str]
) -> tuple[str, str]:
    candidatos = {
        "panel": (
            "Abrir panel de ajustes",
            "Abra el panel de ajustes visible en la interfaz."
        ),
        "menu": (
            "Desplegar selector",
            "Despliegue el menú o selector visible para mostrar sus opciones."
        ),
        "dialogo": (
            "Revisar mensaje del sistema",
            "Revise el cuadro de diálogo o mensaje visible antes de continuar."
        ),
        "valor": (
            "Ajustar control",
            "Ajuste el control o parámetro cuya modificación sea visible en pantalla."
        ),
        "control": (
            "Seleccionar opción",
            "Seleccione la opción o control resaltado en la interfaz."
        ),
        "general": (
            "Confirmar cambio visible",
            "Confirme el cambio visible observado en la interfaz."
        )
    }

    titulo, instruccion = candidatos.get(
        sequence_label,
        ("Confirmar cambio visible", "Confirme el cambio visible observado en la interfaz.")
    )

    if titulo not in titulos_permitidos:
        titulo = "Confirmar cambio visible"

    return titulo, instruccion


def inferir_primary_frame(
    sequence: dict[str, Any],
    events_raw_index: dict[str, dict[str, Any]]
) -> str:
    primary_event_id = sequence.get("primary_event_id", "")
    if primary_event_id and primary_event_id in events_raw_index:
        return events_raw_index[primary_event_id].get("primary_frame", "")

    event_ids = sequence.get("event_ids", [])
    for event_id in reversed(event_ids):
        if event_id in events_raw_index:
            frame_id = events_raw_index[event_id].get("primary_frame", "")
            if frame_id:
                return frame_id

    return ""


def inferir_requires_manual_review(sequence: dict[str, Any]) -> tuple[bool, str]:
    if sequence.get("excluded_from_steps", False):
        return True, "La secuencia está marcada como excluida del flujo principal."

    if sequence.get("is_ambiguous", False):
        return True, "La secuencia contiene ambigüedad y requiere validación manual."

    if sequence.get("certainty", "baja") == "baja":
        return True, "La secuencia tiene certeza baja."

    return False, ""


def construir_steps_normalized(
    timeline_raw: dict[str, Any],
    events_raw: dict[str, Any],
    terminology: dict[str, Any]
) -> dict[str, Any]:
    timeline = timeline_raw.get("timeline", [])
    eventos = events_raw.get("events", [])
    titulos_permitidos = extraer_titulos_normalizados(terminology)

    eventos_por_id = {evento["event_id"]: evento for evento in eventos}

    steps: list[dict[str, Any]] = []
    contador = 1

    for sequence in timeline:
        titulo, instruccion = inferir_titulo_y_instruccion(
            sequence_label=sequence.get("sequence_label", "general"),
            sequence_summary=sequence.get("sequence_summary", ""),
            titulos_permitidos=titulos_permitidos
        )

        requires_manual_review, review_reason = inferir_requires_manual_review(sequence)

        step = {
            "step_id": f"step_{contador:04d}",
            "step_order": contador,
            "title": titulo,
            "instruction": instruccion,
            "start_time": sequence.get("start_time", ""),
            "end_time": sequence.get("end_time", ""),
            "start_seconds": sequence.get("start_seconds", 0.0),
            "end_seconds": sequence.get("end_seconds", 0.0),
            "source_sequence_ids": [sequence.get("sequence_id", "")],
            "source_event_ids": sequence.get("event_ids", []),
            "primary_frame": inferir_primary_frame(sequence, eventos_por_id),
            "certainty": sequence.get("certainty", "baja"),
            "requires_manual_review": requires_manual_review,
            "review_reason": review_reason,
            "technical_notes": sequence.get("sequence_summary", ""),
            "excluded_from_guide": bool(sequence.get("excluded_from_steps", False))
        }

        steps.append(step)
        contador += 1

    resumen = {
        "total_steps": len(steps),
        "high_certainty_steps": sum(1 for s in steps if s["certainty"] == "alta"),
        "medium_certainty_steps": sum(1 for s in steps if s["certainty"] == "media"),
        "low_certainty_steps": sum(1 for s in steps if s["certainty"] == "baja"),
        "manual_review_steps": sum(1 for s in steps if s["requires_manual_review"])
    }

    return {
        "video_id": timeline_raw.get("video_id", ""),
        "run_id": timeline_raw.get("run_id", ""),
        "source_video": timeline_raw.get("source_video", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "step_normalization_config": {
            "source_timeline_raw": "",
            "terminology_version": terminology.get("version", ""),
            "action_lexicon_version": "1.0",
            "allow_merge_sequences": True,
            "max_step_duration_seconds": 0.0
        },
        "summary": resumen,
        "steps": steps
    }


def crear_steps_normalized_desde_timeline(
    timeline_raw_path: str | Path,
    events_raw_path: str | Path,
    terminology_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    timeline_raw = cargar_json(timeline_raw_path)
    events_raw = cargar_json(events_raw_path)
    terminology = cargar_json(terminology_path)

    resultado = construir_steps_normalized(
        timeline_raw=timeline_raw,
        events_raw=events_raw,
        terminology=terminology
    )

    resultado["step_normalization_config"]["source_timeline_raw"] = str(timeline_raw_path)
    guardar_json(output_path, resultado)
    return resultado

