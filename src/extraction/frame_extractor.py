from __future__ import annotations

from pathlib import Path
from typing import Any
from hashlib import sha1
import subprocess
import json

from PIL import Image, ImageChops, ImageStat


def ejecutar_comando(comando: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Error ejecutando comando: {' '.join(comando)}\n\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}"
        ) from e


def extraer_frames_uniformes(
    video_path: str | Path,
    output_dir: str | Path,
    target_fps: float
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    patron_salida = output_dir / "frame_%06d.jpg"

    comando = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", f"fps={target_fps}",
        str(patron_salida)
    ]

    ejecutar_comando(comando)

    return sorted(output_dir.glob("frame_*.jpg"))


def calcular_hash_archivo(ruta: str | Path) -> str:
    ruta = Path(ruta)
    contenido = ruta.read_bytes()
    return sha1(contenido).hexdigest()[:12]


def obtener_dimensiones_imagen(ruta: str | Path) -> tuple[int, int]:
    with Image.open(ruta) as img:
        return img.size


def diferencia_normalizada(img1: Image.Image, img2: Image.Image) -> float:
    diff = ImageChops.difference(img1, img2)
    stat = ImageStat.Stat(diff)
    media_canales = stat.mean
    media_global = sum(media_canales) / len(media_canales)
    return round(media_global / 255.0, 4)


def recortar_region(img: Image.Image, region: tuple[float, float, float, float]) -> Image.Image:
    ancho, alto = img.size
    x1 = int(region[0] * ancho)
    y1 = int(region[1] * alto)
    x2 = int(region[2] * ancho)
    y2 = int(region[3] * alto)
    return img.crop((x1, y1, x2, y2))


def calcular_diferencias_por_region(
    ruta_anterior: str | Path,
    ruta_actual: str | Path
) -> dict[str, float]:
    with Image.open(ruta_anterior) as img1, Image.open(ruta_actual) as img2:
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")

        if img1.size != img2.size:
            img2 = img2.resize(img1.size)

        regiones = {
            "global": (0.0, 0.0, 1.0, 1.0),
            "barra_superior": (0.0, 0.0, 1.0, 0.08),
            "panel_izquierdo": (0.0, 0.08, 0.34, 0.95),
            "panel_central": (0.28, 0.18, 0.74, 0.74)
        }

        resultados: dict[str, float] = {}

        for nombre, region in regiones.items():
            sub1 = recortar_region(img1, region)
            sub2 = recortar_region(img2, region)
            resultados[nombre] = diferencia_normalizada(sub1, sub2)

        return resultados


def inferir_visual_flags_regionales(
    diferencias: dict[str, float],
    umbral_global: float,
    umbral_superior: float,
    umbral_izquierdo: float,
    umbral_central: float
) -> list[str]:
    flags: list[str] = []

    if diferencias["global"] >= umbral_global:
        flags.append("cambio_interfaz_visible")

    if diferencias["barra_superior"] >= umbral_superior:
        flags.append("cambio_barra_superior_visible")

    if diferencias["panel_izquierdo"] >= umbral_izquierdo:
        flags.append("cambio_panel_izquierdo_visible")

    if diferencias["panel_central"] >= umbral_central:
        flags.append("cambio_panel_central_visible")

    return flags


def construir_frames_metadata_desde_frames(
    frame_paths: list[Path],
    target_fps: float,
    umbral_candidato: float = 0.02,
    umbral_keyframe: float = 0.05,
    umbral_global: float = 0.025,
    umbral_superior: float = 0.02,
    umbral_izquierdo: float = 0.03,
    umbral_central: float = 0.03
) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    intervalo = 1.0 / target_fps if target_fps > 0 else 1.0

    frame_anterior: Path | None = None

    for i, frame_path in enumerate(frame_paths):
        timestamp_seconds = round(i * intervalo, 4)
        width, height = obtener_dimensiones_imagen(frame_path)

        if frame_anterior is None:
            diferencias = {
                "global": 0.0,
                "barra_superior": 0.0,
                "panel_izquierdo": 0.0,
                "panel_central": 0.0
            }
        else:
            diferencias = calcular_diferencias_por_region(frame_anterior, frame_path)

        change_score_prev = diferencias["global"]
        change_score_max_region = max(
            diferencias["barra_superior"],
            diferencias["panel_izquierdo"],
            diferencias["panel_central"]
        )

        is_candidate = change_score_max_region >= umbral_candidato or i == 0
        is_keyframe = change_score_max_region >= umbral_keyframe

        visual_flags = inferir_visual_flags_regionales(
            diferencias=diferencias,
            umbral_global=umbral_global,
            umbral_superior=umbral_superior,
            umbral_izquierdo=umbral_izquierdo,
            umbral_central=umbral_central
        )

        metadata.append({
            "frame_id": f"frame_{i+1:06d}",
            "frame_number_source": None,
            "timestamp_seconds": timestamp_seconds,
            "image_path": str(frame_path).replace("\\", "/"),
            "image_hash": calcular_hash_archivo(frame_path),
            "width": width,
            "height": height,
            "extraction_type": "uniform",
            "is_keyframe": is_keyframe,
            "is_candidate": is_candidate,
            "change_score_prev": change_score_prev,
            "change_score_next": 0.0,
            "change_score_max_region": change_score_max_region,
            "diff_regiones": diferencias,
            "duplicate_group": None,
            "visual_flags": visual_flags,
            "technical_notes": "Frame extraído automáticamente desde video real con análisis regional."
        })

        frame_anterior = frame_path

    for i in range(len(metadata) - 1):
        metadata[i]["change_score_next"] = metadata[i + 1]["change_score_prev"]

    return metadata


def guardar_json(ruta: str | Path, contenido: Any) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def extraer_y_generar_frames_metadata(
    video_path: str | Path,
    run_dir: str | Path,
    target_fps: float,
    umbral_candidato: float = 0.02,
    umbral_keyframe: float = 0.05,
    umbral_global: float = 0.025,
    umbral_superior: float = 0.02,
    umbral_izquierdo: float = 0.03,
    umbral_central: float = 0.03
) -> Path:
    run_dir = Path(run_dir)
    frames_dir = run_dir / "frames"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = extraer_frames_uniformes(
        video_path=video_path,
        output_dir=frames_dir,
        target_fps=target_fps
    )

    metadata = construir_frames_metadata_desde_frames(
        frame_paths=frame_paths,
        target_fps=target_fps,
        umbral_candidato=umbral_candidato,
        umbral_keyframe=umbral_keyframe,
        umbral_global=umbral_global,
        umbral_superior=umbral_superior,
        umbral_izquierdo=umbral_izquierdo,
        umbral_central=umbral_central
    )

    metadata_path = logs_dir / "frames_metadata_generated.json"
    guardar_json(metadata_path, metadata)
    return metadata_path
