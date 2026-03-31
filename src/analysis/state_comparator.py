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


def son_equivalentes_para_consolidacion(
    actual: dict[str, Any],
    siguiente: dict[str, Any]
) -> bool:
    etiqueta_actual = actual.get("interpreted_label", "")
    etiqueta_siguiente = siguiente.get("interpreted_label", "")

    if etiqueta_actual == etiqueta_siguiente:
        return True

    equivalencias = {
        ("persistencia_formulario_login", "campo_usuario_visible"),
        ("campo_usuario_visible", "persistencia_formulario_login")
    }

    return (etiqueta_actual, etiqueta_siguiente) in equivalencias


def consolidar_bloque(bloque: list[dict[str, Any]], orden: int) -> dict[str, Any]:
    primero = bloque[0]
    ultimo = bloque[-1]

    etiquetas = [item.get("interpreted_label", "") for item in bloque]
    tipos = [item.get("interpreted_event_type", "") for item in bloque]
    confidencias = [float(item.get("confidence", 0.0)) for item in bloque]

    if "apertura_cuadro_inicio_sesion" in etiquetas:
        consolidated_type = "estado_login"
        consolidated_label = "apertura_cuadro_inicio_sesion"
        descripcion = "Aparece o se consolida el cuadro de inicio de sesión."
    elif any(et in {"persistencia_formulario_login", "campo_usuario_visible"} for et in etiquetas):
        consolidated_type = "estado_login"
        consolidated_label = "estado_login_visible"
        descripcion = "Se mantiene visible un estado de inicio de sesión con campo de usuario."
    elif "transicion_visual_relevante_no_clasificada" in etiquetas:
        consolidated_type = "transicion_visual"
        consolidated_label = "transicion_visual_relevante_no_clasificada"
        descripcion = "Se detecta una transición visual relevante no clasificada."
    else:
        consolidated_type = tipos[0] if tipos else "estado_visual"
        consolidated_label = etiquetas[0] if etiquetas else "estado_visual_no_clasificado"
        descripcion = primero.get("descripcion", "Estado visual consolidado.")

    return {
        "state_change_id": f"chg_{orden:04d}",
        "sequence_order": orden,
        "start_time": primero.get("timestamp", ""),
        "end_time": ultimo.get("timestamp", ""),
        "start_seconds": primero.get("timestamp_seconds", 0.0),
        "end_seconds": ultimo.get("timestamp_seconds", 0.0),
        "frame_ids": [item.get("frame_id", "") for item in bloque],
        "primary_frame": primero.get("frame_id", ""),
        "consolidated_type": consolidated_type,
        "consolidated_label": consolidated_label,
        "descripcion": descripcion,
        "confidence": round(sum(confidencias) / len(confidencias), 4) if confidencias else 0.0,
        "source_interpreted_labels": etiquetas,
        "needs_fallback_generic_label": any(bool(item.get("needs_fallback_generic_label", True)) for item in bloque)
    }


def construir_state_changes(events_interpreted: dict[str, Any]) -> dict[str, Any]:
    items = events_interpreted.get("events_interpreted", [])

    if not items:
        return {
            "video_id": events_interpreted.get("video_id", ""),
            "run_id": events_interpreted.get("run_id", ""),
            "source_video": events_interpreted.get("source_video", ""),
            "state_change_config": {
                "modo": "consolidacion_secuencial",
                "fusiona_persistencias": True
            },
            "summary": {
                "total_state_changes": 0
            },
            "state_changes": []
        }

    bloques: list[list[dict[str, Any]]] = []
    bloque_actual: list[dict[str, Any]] = [items[0]]

    for i in range(1, len(items)):
        anterior = items[i - 1]
        actual = items[i]

        if son_equivalentes_para_consolidacion(anterior, actual):
            bloque_actual.append(actual)
        else:
            bloques.append(bloque_actual)
            bloque_actual = [actual]

    if bloque_actual:
        bloques.append(bloque_actual)

    state_changes = [
        consolidar_bloque(bloque, orden=i + 1)
        for i, bloque in enumerate(bloques)
    ]

    return {
        "video_id": events_interpreted.get("video_id", ""),
        "run_id": events_interpreted.get("run_id", ""),
        "source_video": events_interpreted.get("source_video", ""),
        "state_change_config": {
            "modo": "consolidacion_secuencial",
            "fusiona_persistencias": True
        },
        "summary": {
            "total_state_changes": len(state_changes)
        },
        "state_changes": state_changes
    }


def crear_state_changes(
    events_interpreted_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    events_interpreted = cargar_json(events_interpreted_path)
    resultado = construir_state_changes(events_interpreted)
    guardar_json(output_path, resultado)
    return resultado
