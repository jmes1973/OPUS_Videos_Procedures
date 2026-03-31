from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re


PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def es_texto_relevante(texto: str, confianza: float) -> bool:
    texto = normalizar_texto(texto)

    if not texto:
        return False

    if confianza < 0.30:
        return False

    if len(texto) == 1 and texto not in {"@", ".", "_", "-"}:
        return False

    ruido_comun = {
        "—", "-", "_", "I<", "I<]", "I<)", "Vv", "eee", "%", "4", ">", "v", "See"
    }

    if texto in ruido_comun:
        return False

    return True


def detectar_elementos_inferidos(
    frame_index_item: dict[str, Any],
    ocr_item: dict[str, Any]
) -> tuple[list[str], list[str], str, float]:
    visual_flags = set(frame_index_item.get("visual_flags", []))
    textos_visibles = ocr_item.get("textos_visibles", [])
    ocr_calidad = float(ocr_item.get("ocr_calidad_global", 0.0))
    is_keyframe = bool(frame_index_item.get("is_keyframe", False))
    is_candidate = bool(frame_index_item.get("is_candidate", False))

    textos_relevantes: list[str] = []
    elementos_inferidos: list[str] = []

    for item in textos_visibles:
        texto = normalizar_texto(item.get("texto", ""))
        confianza = float(item.get("confianza", 0.0))

        if es_texto_relevante(texto, confianza):
            textos_relevantes.append(texto)

    textos_relevantes = list(dict.fromkeys(textos_relevantes))

    hay_correo = any(PATRON_CORREO.match(texto) for texto in textos_relevantes)

    if hay_correo:
        elementos_inferidos.append("campo_usuario_visible")

    if hay_correo and ocr_calidad >= 0.55:
        elementos_inferidos.append("posible_formulario_login_visible")

    if "cambio_interfaz_visible" in visual_flags and not textos_relevantes:
        elementos_inferidos.append("cambio_visual_sin_texto_legible")

    if is_keyframe and "cambio_interfaz_visible" in visual_flags:
        elementos_inferidos.append("hito_visual_relevante")

    if is_candidate and not is_keyframe and hay_correo:
        elementos_inferidos.append("estado_login_persistente")

    elementos_inferidos = list(dict.fromkeys(elementos_inferidos))

    if "posible_formulario_login_visible" in elementos_inferidos:
        observacion = "Se observa un posible formulario de inicio de sesión con un campo de usuario visible."
        confianza_base = 0.78
    elif "cambio_visual_sin_texto_legible" in elementos_inferidos and "hito_visual_relevante" in elementos_inferidos:
        observacion = "Se detecta un cambio relevante de interfaz sin texto legible suficiente."
        confianza_base = 0.68
    elif "campo_usuario_visible" in elementos_inferidos:
        observacion = "Se observa un campo de usuario visible en la interfaz."
        confianza_base = 0.72
    elif "hito_visual_relevante" in elementos_inferidos:
        observacion = "Se detecta un hito visual relevante en la interfaz."
        confianza_base = 0.66
    else:
        observacion = "No se detectan elementos suficientes para una observación específica."
        confianza_base = 0.35

    return textos_relevantes, elementos_inferidos, observacion, confianza_base


def indexar_observaciones_ocr(ocr_observations: dict[str, Any]) -> dict[str, dict[str, Any]]:
    observations = ocr_observations.get("observations", [])
    return {obs["frame_id"]: obs for obs in observations if "frame_id" in obs}


def construir_frame_observations(
    frames_index: dict[str, Any],
    ocr_observations: dict[str, Any]
) -> dict[str, Any]:
    frames = frames_index.get("frames", [])
    ocr_por_frame = indexar_observaciones_ocr(ocr_observations)

    observations: list[dict[str, Any]] = []

    for frame in frames:
        frame_id = frame.get("frame_id", "")
        ocr_item = ocr_por_frame.get(frame_id, {
            "textos_visibles": [],
            "ocr_calidad_global": 0.0
        })

        textos_relevantes, elementos_inferidos, observacion, confianza_base = detectar_elementos_inferidos(
            frame_index_item=frame,
            ocr_item=ocr_item
        )

        observations.append({
            "frame_id": frame_id,
            "timestamp": frame.get("timestamp", ""),
            "timestamp_seconds": frame.get("timestamp_seconds", 0.0),
            "image_path": frame.get("image_path", ""),
            "ocr_calidad_global": float(ocr_item.get("ocr_calidad_global", 0.0)),
            "textos_relevantes": textos_relevantes,
            "elementos_inferidos": elementos_inferidos,
            "observacion_objetiva": observacion,
            "confianza_base": confianza_base
        })

    return {
        "video_id": frames_index.get("video_id", ""),
        "run_id": frames_index.get("run_id", ""),
        "source_video": frames_index.get("source_video", ""),
        "observation_config": {
            "usa_ocr": True,
            "usa_flags_visuales": True,
            "modo": "capa_1_determinista"
        },
        "observations": observations
    }


def crear_frame_observations(
    frames_index_path: str | Path,
    ocr_observations_path: str | Path,
    output_path: str | Path
) -> dict[str, Any]:
    frames_index = cargar_json(frames_index_path)
    ocr_observations = cargar_json(ocr_observations_path)

    resultado = construir_frame_observations(
        frames_index=frames_index,
        ocr_observations=ocr_observations
    )

    guardar_json(output_path, resultado)
    return resultado
