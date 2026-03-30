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


def son_eventos_agrupables(
    evento_actual: dict[str, Any],
    evento_siguiente: dict[str, Any],
    ventana_maxima_segundos: float = 2.0
) -> bool:
    fin_actual = float(evento_actual.get("end_seconds", 0.0))
    inicio_siguiente = float(evento_siguiente.get("start_seconds", 0.0))

    if inicio_siguiente - fin_actual > ventana_maxima_segundos:
        return False

    tipo_actual = evento_actual.get("event_type", "")
    tipo_siguiente = evento_siguiente.get("event_type", "")

    accion_actual = evento_actual.get("observable_action", "")
    accion_siguiente = evento_siguiente.get("observable_action", "")

    familias_relacionadas = [
        {"transicion_interfaz", "cambio_menu", "cambio_control"},
        {"dialogo", "cambio_control"},
        {"cambio_valor", "cambio_control"},
        {"persistencia_interfaz", "transicion_interfaz"}
    ]

    mismo_tipo = tipo_actual == tipo_siguiente
    acciones_relacionadas = accion_actual == accion_siguiente

    comparte_familia = any(
        tipo_actual in familia and tipo_siguiente in familia
        for familia in familias_relacionadas
    )

    return mismo_tipo or acciones_relacionadas or comparte_familia


def resumir_secuencia(eventos: list[dict[str, Any]]) -> str:
    acciones = [evento.get("observable_action", "") for evento in eventos]

    if not acciones:
        return "Secuencia sin acciones identificadas"

    if "aparece_panel_lateral" in acciones and "se_despliega_menu" in acciones:
        return "Apertura de panel y despliegue de menú"

    if "se_despliega_menu" in acciones and "cambia_seleccion_visible" in acciones:
        return "Despliegue de menú y cambio de selección visible"

    if "aparece_cuadro_dialogo" in acciones:
        return "Aparición de cuadro de diálogo"

    if "cambia_valor_visible" in acciones:
        return "Cambio visible en un valor o parámetro"

    if len(acciones) == 1:
        return acciones[0].replace("_", " ")

    return "Secuencia de eventos relacionados de interfaz"


def inferir_etiqueta_secuencia(eventos: list[dict[str, Any]]) -> str:
    acciones = [evento.get("observable_action", "") for evento in eventos]

    if "aparece_panel_lateral" in acciones:
        return "panel"
    if "se_despliega_menu" in acciones:
        return "menu"
    if "aparece_cuadro_dialogo" in acciones:
        return "dialogo"
    if "cambia_valor_visible" in acciones:
        return "valor"
    if "se_resalta_boton" in acciones:
        return "control"

    return "general"


def inferir_certeza_secuencia(eventos: list[dict[str, Any]]) -> str:
    niveles = [evento.get("certainty", "baja") for evento in eventos]

    if not niveles:
        return "baja"

    if all(nivel == "alta" for nivel in niveles):
        return "alta"

    if "media" in niveles or ("alta" in niveles and "baja" in niveles):
        return "media"

    return "baja"


def construir_timeline_desde_eventos(events_raw: dict[str, Any]) -> dict[str, Any]:
    eventos = events_raw.get("events", [])

    if not eventos:
        return {
            "video_id": events_raw.get("video_id", ""),
            "run_id": events_raw.get("run_id", ""),
            "source_video": events_raw.get("source_video", ""),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "timeline_config": {
                "source_events_raw": "",
                "grouping_strategy": "eventos_consecutivos_relacionados",
                "allow_single_event_sequences": True
            },
            "summary": {
                "total_sequences": 0,
                "total_linked_events": 0,
                "sequences_with_ambiguity": 0
            },
            "timeline": []
        }

    secuencias: list[list[dict[str, Any]]] = []
    secuencia_actual: list[dict[str, Any]] = [eventos[0]]

    for i in range(1, len(eventos)):
        previo = eventos[i - 1]
        actual = eventos[i]

        if son_eventos_agrupables(previo, actual):
            secuencia_actual.append(actual)
        else:
            secuencias.append(secuencia_actual)
            secuencia_actual = [actual]

    if secuencia_actual:
        secuencias.append(secuencia_actual)

    timeline: list[dict[str, Any]] = []

    for indice, secuencia in enumerate(secuencias, start=1):
        primer_evento = secuencia[0]
        ultimo_evento = secuencia[-1]

        event_ids = [evento["event_id"] for evento in secuencia]
        secuencia_ambigua = any(evento.get("is_ambiguous", False) for evento in secuencia)
        excluded_from_steps = all(evento.get("excluded_from_steps", False) for evento in secuencia)

        timeline.append({
            "sequence_id": f"seq_{indice:04d}",
            "sequence_order": indice,
            "start_time": primer_evento["start_time"],
            "end_time": ultimo_evento["end_time"],
            "start_seconds": primer_evento["start_seconds"],
            "end_seconds": ultimo_evento["end_seconds"],
            "event_ids": event_ids,
            "primary_event_id": secuencia[-1]["event_id"],
            "sequence_label": inferir_etiqueta_secuencia(secuencia),
            "sequence_summary": resumir_secuencia(secuencia),
            "certainty": inferir_certeza_secuencia(secuencia),
            "is_ambiguous": secuencia_ambigua,
            "ambiguity_reason": "La secuencia contiene al menos un evento ambiguo." if secuencia_ambigua else "",
            "excluded_from_steps": excluded_from_steps
        })

    return {
        "video_id": events_raw.get("video_id", ""),
        "run_id": events_raw.get("run_id", ""),
        "source_video": events_raw.get("source_video", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "timeline_config": {
            "source_events_raw": "",
            "grouping_strategy": "eventos_consecutivos_relacionados",
            "allow_single_event_sequences": True
        },
        "summary": {
            "total_sequences": len(timeline),
            "total_linked_events": len(eventos),
            "sequences_with_ambiguity": sum(1 for sec in timeline if sec["is_ambiguous"])
        },
        "timeline": timeline
    }


def crear_timeline_raw_desde_events_raw(
    events_raw_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    events_raw = cargar_json(events_raw_path)
    resultado = construir_timeline_desde_eventos(events_raw)
    resultado["timeline_config"]["source_events_raw"] = str(events_raw_path)
    guardar_json(output_path, resultado)
    return resultado
