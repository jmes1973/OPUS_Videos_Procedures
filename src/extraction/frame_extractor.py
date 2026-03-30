from __future__ import annotations

from pathlib import Path
from typing import Any
from hashlib import sha1
import subprocess
import json
import math


def ejecutar_comando(comando: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )


def obtener_duracion_video(video_path: str | Path) -> float:
    comando = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    resultado = ejecutar_comando(comando)
    return float(resultado.stdout.strip())


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


def construir_frames_metadata_desde_frames(
    frame_paths: list[Path],
    run_frames_dir: str | Path,
    target_fps: float
) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []

    intervalo = 1.0 / target_fps if target_fps > 0 else 1.0

    for i, frame_path in enumerate(frame_paths):
        timestamp_seconds = round(i * intervalo, 4)

        metadata.append({
            "frame_id": f"frame_{i+1:06d}",
            "frame_number_source": None,
            "timestamp_seconds": timestamp_seconds,
            "image_path": str(frame_path).replace("\\", "/"),
            "image_hash": calcular_hash_archivo(frame_path),
            "width": 0,
            "height": 0,
            "extraction_type": "uniform",
            "is_keyframe": False,
            "is_candidate": True,
            "change_score_prev": 0.0 if i == 0 else 0.2,
            "change_score_next": 0.0,
            "duplicate_group": None,
            "visual_flags": [],
            "technical_notes": "Frame extraído automáticamente desde video real."
        })

    return metadata


def guardar_json(ruta: str | Path, contenido: Any) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def extraer_y_generar_frames_metadata(
    video_path: str | Path,
    run_dir: str | Path,
    target_fps: float
) -> Path:
    run_dir = Path(run_dir)
    frames_dir = run_dir / "frames"
    cache_dir = run_dir / "logs"
    cache_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = extraer_frames_uniformes(
        video_path=video_path,
        output_dir=frames_dir,
        target_fps=target_fps
    )

    metadata = construir_frames_metadata_desde_frames(
        frame_paths=frame_paths,
        run_frames_dir=frames_dir,
        target_fps=target_fps
    )

    metadata_path = run_dir / "logs" / "frames_metadata_generated.json"
    guardar_json(metadata_path, metadata)
    return metadata_path
