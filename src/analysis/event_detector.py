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


def construir_indice_acciones(action_lexicon: dict[str, Any]) -> set[str]:
    acciones = action_lexicon.get("acciones", [])
    return {accion["canonico"] for accion in acciones if "canonico" in accion}


def obtener_marcas(frame: dict[str, Any]) -> set[str]:
    return set(frame.get("visual_flags", []))


def inferir_certeza(
    evidencia_frames: list[str],
    change_score: float,
    is_keyframe: bool
) -> str:
    puntuacion = 0

    if len(evidencia_frames) >= 2:
        puntuacion += 1
    if change_score >= 0.35:
        puntuacion += 1
    if is_keyframe:
        puntuacion += 1

    if puntuacion >= 3:
        return "alta"
    if puntuacion == 2:
        return "media"
    return "baja"


def crear_evento(
    event_id: str,
    sequence_order: int,
    start_frame: dict[str, Any],
    end_frame: dict[str, Any],
    event_type: str,
    observable_action: str,
    evidence_frames: list[str],
    certainty: str,
    is_ambiguous: bool,
    ambiguity_reason: str,
    visual_flags: list[str],
    technical_notes: str,
    excluded_from_steps: bool = False
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "sequence_order": sequence_order,
        "start_time": start_frame["timestamp"],
        "end_time": end_frame["timestamp"],
        "start_seconds": start_frame["timestamp_seconds"],
        "end_seconds": end_frame["timestamp_seconds"],
        "event_type": event_type,
        "observable_action": observable_action,
        "evidence_frames": evidence_frames,
        "primary_frame": evidence_frames[-1] if evidence_frames else "",
        "certainty": certainty,
        "is_ambiguous": is_ambiguous,
        "ambiguity_reason": ambiguity_reason,
        "visual_flags": visual_flags,
        "technical_notes": technical_notes,
        "excluded_from_steps": excluded_from_steps
    }


def detectar_eventos_desde_frames(
    frames_index: dict[str, Any],
    action_lexicon: dict[str, Any],
    terminology: dict[str, Any]
) -> dict[str, Any]:
    frames = frames_index.get("frames", [])
    acciones_validas = construir_indice_acciones(action_lexicon)
    marcas_permitidas = set(terminology.get("marcas_visuales_permitidas", []))

    eventos: list[dict[str, Any]] = []
    contador_eventos = 1

    if not frames:
        return {
            "video_id": frames_index.get("video_id", ""),
            "run_id": frames_index.get("run_id", ""),
            "source_video": frames_index.get("source_video", ""),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "event_detection_config": {
                "source_frames_index": "",
                "event_types_version": "1.0",
                "analysis_rules_version": "1.0",
                "minimum_evidence_frames": 2,
                "allow_ambiguous_events": True
            },
            "summary": {
                "total_events": 0,
                "high_certainty_events": 0,
                "medium_certainty_events": 0,
                "low_certainty_events": 0,
                "ambiguous_events": 0
            },
            "events": []
        }

    for i in range(1, len(frames)):
        anterior = frames[i - 1]
        actual = frames[i]

        marcas_anteriores = obtener_marcas(anterior)
        marcas_actuales = obtener_marcas(actual)

        nuevas_marcas = list((marcas_actuales - marcas_anteriores) & marcas_permitidas)
        marcas_perdidas = list((marcas_anteriores - marcas_actuales) & marcas_permitidas)
        marcas_comunes = list((marcas_actuales & marcas_anteriores) & marcas_permitidas)

        change_score = float(actual.get("change_score_prev", 0.0))
        is_keyframe = bool(actual.get("is_keyframe", False))
        is_candidate = bool(actual.get("is_candidate", False))

        evento_detectado = None

        if "panel_visible" in nuevas_marcas and "aparece_panel_lateral" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="transicion_interfaz",
                observable_action="aparece_panel_lateral",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="Se observa transición hacia un panel visible."
            )

        elif "panel_visible" in marcas_perdidas and "desaparece_panel_lateral" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="transicion_interfaz",
                observable_action="desaparece_panel_lateral",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="El panel deja de estar visible."
            )

        elif "desplegable_visible" in nuevas_marcas and "se_despliega_menu" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="cambio_menu",
                observable_action="se_despliega_menu",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="Se hace visible un menú desplegable."
            )

        elif "desplegable_visible" in marcas_perdidas and "se_cierra_menu" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="cambio_menu",
                observable_action="se_cierra_menu",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="El menú desplegable deja de estar visible."
            )

        elif "dialogo_visible" in nuevas_marcas and "aparece_cuadro_dialogo" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="dialogo",
                observable_action="aparece_cuadro_dialogo",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="Se observa la aparición de un cuadro de diálogo."
            )

        elif "dialogo_visible" in marcas_perdidas and "desaparece_cuadro_dialogo" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="dialogo",
                observable_action="desaparece_cuadro_dialogo",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="El cuadro de diálogo deja de estar visible."
            )

        elif "boton_resaltado" in nuevas_marcas and "se_resalta_boton" in acciones_validas:
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="cambio_control",
                observable_action="se_resalta_boton",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe),
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="Un botón presenta realce visual."
            )

        elif (
            is_candidate
            and change_score >= 0.20
            and "cambio_interfaz_visible" in marcas_actuales
            and "cambia_valor_visible" in acciones_validas
        ):
            certeza = inferir_certeza([anterior["frame_id"], actual["frame_id"]], change_score, is_keyframe)
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="cambio_valor",
                observable_action="cambia_valor_visible",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty=certeza,
                is_ambiguous=certeza == "baja",
                ambiguity_reason="Cambio visible sin elemento específico claramente identificable." if certeza == "baja" else "",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="Se detecta un cambio visible en la interfaz."
            )

        elif (
            "panel_visible" in marcas_comunes
            and change_score < 0.10
            and "permanece_panel_visible" in acciones_validas
        ):
            evento_detectado = crear_evento(
                event_id=f"evt_{contador_eventos:04d}",
                sequence_order=contador_eventos,
                start_frame=anterior,
                end_frame=actual,
                event_type="persistencia_interfaz",
                observable_action="permanece_panel_visible",
                evidence_frames=[anterior["frame_id"], actual["frame_id"]],
                certainty="media",
                is_ambiguous=False,
                ambiguity_reason="",
                visual_flags=sorted(list((marcas_anteriores | marcas_actuales) & marcas_permitidas)),
                technical_notes="El panel permanece visible sin cambios relevantes.",
                excluded_from_steps=True
            )

        if evento_detectado:
            eventos.append(evento_detectado)
            contador_eventos += 1

    resumen = {
        "total_events": len(eventos),
        "high_certainty_events": sum(1 for e in eventos if e["certainty"] == "alta"),
        "medium_certainty_events": sum(1 for e in eventos if e["certainty"] == "media"),
        "low_certainty_events": sum(1 for e in eventos if e["certainty"] == "baja"),
        "ambiguous_events": sum(1 for e in eventos if e["is_ambiguous"])
    }

    return {
        "video_id": frames_index.get("video_id", ""),
        "run_id": frames_index.get("run_id", ""),
        "source_video": frames_index.get("source_video", ""),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "event_detection_config": {
            "source_frames_index": "",
            "event_types_version": "1.0",
            "analysis_rules_version": "1.0",
            "minimum_evidence_frames": 2,
            "allow_ambiguous_events": True
        },
        "summary": resumen,
        "events": eventos
    }


def crear_events_raw_desde_frames_index(
    frames_index_path: str | Path,
    action_lexicon_path: str | Path,
    terminology_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    frames_index = cargar_json(frames_index_path)
    action_lexicon = cargar_json(action_lexicon_path)
    terminology = cargar_json(terminology_path)

    resultado = detectar_eventos_desde_frames(
        frames_index=frames_index,
        action_lexicon=action_lexicon,
        terminology=terminology
    )

    resultado["event_detection_config"]["source_frames_index"] = str(frames_index_path)
    guardar_json(output_path, resultado)
    return resultado

