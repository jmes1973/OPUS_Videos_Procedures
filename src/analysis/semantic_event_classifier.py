from __future__ import annotations

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
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def clasificar_observacion(
    observacion: dict[str, Any]
) -> dict[str, Any]:
    frame_id = observacion.get("frame_id", "")
    timestamp = observacion.get("timestamp", "")
    timestamp_seconds = observacion.get("timestamp_seconds", 0.0)
    image_path = observacion.get("image_path", "")
    elementos = set(observacion.get("elementos_inferidos", []))
    textos_relevantes = observacion.get("textos_relevantes", [])
    observacion_objetiva = observacion.get("observacion_objetiva", "")
    confianza_base = float(observacion.get("confianza_base", 0.0))

    interpreted_event_type = "sin_evento_semantico"
    interpreted_label = "sin_evento_semantico"
    descripcion = "No se detecta un evento semántico suficientemente específico."
    confidence = 0.0
    needs_fallback_generic_label = True
    evidence_basis: list[str] = []

    if "posible_formulario_login_visible" in elementos and "hito_visual_relevante" in elementos:
        interpreted_event_type = "aparicion_modal"
        interpreted_label = "apertura_cuadro_inicio_sesion"
        descripcion = "Aparece o se consolida un posible cuadro de inicio de sesión."
        confidence = min(0.92, max(0.75, confianza_base))
        needs_fallback_generic_label = False
        evidence_basis = [
            "posible_formulario_login_visible",
            "hito_visual_relevante"
        ]

    elif "posible_formulario_login_visible" in elementos:
        interpreted_event_type = "persistencia_modal"
        interpreted_label = "persistencia_formulario_login"
        descripcion = "Se mantiene visible un posible formulario de inicio de sesión."
        confidence = min(0.85, max(0.65, confianza_base))
        needs_fallback_generic_label = False
        evidence_basis = [
            "posible_formulario_login_visible"
        ]

    elif "cambio_visual_sin_texto_legible" in elementos and "hito_visual_relevante" in elementos:
        interpreted_event_type = "transicion_visual"
        interpreted_label = "transicion_visual_relevante_no_clasificada"
        descripcion = "Se detecta una transición visual relevante sin texto legible suficiente para clasificarla."
        confidence = min(0.8, max(0.62, confianza_base))
        needs_fallback_generic_label = True
        evidence_basis = [
            "cambio_visual_sin_texto_legible",
            "hito_visual_relevante"
        ]

    elif "campo_usuario_visible" in elementos:
        interpreted_event_type = "elemento_login"
        interpreted_label = "campo_usuario_visible"
        descripcion = "Se observa un campo de usuario visible en la interfaz."
        confidence = min(0.78, max(0.58, confianza_base))
        needs_fallback_generic_label = True
        evidence_basis = [
            "campo_usuario_visible"
        ]

    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "timestamp_seconds": timestamp_seconds,
        "image_path": image_path,
        "interpreted_event_type": interpreted_event_type,
        "interpreted_label": interpreted_label,
        "descripcion": descripcion,
        "confidence": round(confidence, 4),
        "evidence_basis": evidence_basis,
        "observacion_objetiva": observacion_objetiva,
        "textos_relevantes": textos_relevantes,
        "needs_fallback_generic_label": needs_fallback_generic_label
    }


def construir_events_interpreted(
    frame_observations: dict[str, Any]
) -> dict[str, Any]:
    observations = frame_observations.get("observations", [])

    interpreted: list[dict[str, Any]] = []

    for obs in observations:
        clasificado = clasificar_observacion(obs)

        if clasificado["interpreted_label"] != "sin_evento_semantico":
            interpreted.append(clasificado)

    return {
        "video_id": frame_observations.get("video_id", ""),
        "run_id": frame_observations.get("run_id", ""),
        "source_video": frame_observations.get("source_video", ""),
        "semantic_config": {
            "modo": "capa_2_semantica_controlada",
            "usa_observaciones_frame": True,
            "permitir_clasificacion_generica": True
        },
        "summary": {
            "total_interpreted_events": len(interpreted),
            "specific_events": sum(1 for item in interpreted if not item["needs_fallback_generic_label"]),
            "generic_events": sum(1 for item in interpreted if item["needs_fallback_generic_label"])
        },
        "events_interpreted": interpreted
    }


def crear_events_interpreted(
    frame_observations_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    frame_observations = cargar_json(frame_observations_path)

    resultado = construir_events_interpreted(
        frame_observations=frame_observations
    )

    guardar_json(output_path, resultado)
    return resultado
