from __future__ import annotations

from pathlib import Path
import argparse
import json
import math
import subprocess
from typing import Any


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
            "Error ejecutando comando:\n"
            f"{' '.join(comando)}\n\n"
            f"STDOUT:\n{e.stdout}\n\n"
            f"STDERR:\n{e.stderr}"
        ) from e


def obtener_duracion_video(video_path: str | Path) -> float:
    video_path = Path(video_path)

    comando = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    resultado = ejecutar_comando(comando)
    return float(resultado.stdout.strip())


def segundos_a_hhmmss(segundos: float) -> str:
    segundos = int(round(segundos))
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    return f"{h:02d}{m:02d}{s:02d}"


def segundos_a_timestamp(segundos: float) -> str:
    segundos = int(round(segundos))
    h = segundos // 3600
    m = (segundos % 3600) // 60
    s = segundos % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def crear_plan_segmentos(
    video_id: str,
    video_path: str | Path,
    duracion_segmento_min: float
) -> list[dict[str, Any]]:
    duracion_total = obtener_duracion_video(video_path)
    duracion_segmento = duracion_segmento_min * 60

    total_segmentos = math.ceil(duracion_total / duracion_segmento)
    segmentos: list[dict[str, Any]] = []

    for i in range(total_segmentos):
        inicio = i * duracion_segmento
        fin = min((i + 1) * duracion_segmento, duracion_total)

        segmento_id = f"{video_id}_S{i + 1:02d}"
        nombre_archivo = (
            f"{segmento_id}_"
            f"{segundos_a_hhmmss(inicio)}_"
            f"{segundos_a_hhmmss(fin)}.mp4"
        )

        segmentos.append({
            "video_id": video_id,
            "segmento_id": segmento_id,
            "segmento_numero": i + 1,
            "inicio_segundos": round(inicio, 3),
            "fin_segundos": round(fin, 3),
            "inicio": segundos_a_timestamp(inicio),
            "fin": segundos_a_timestamp(fin),
            "duracion_segundos": round(fin - inicio, 3),
            "archivo_salida": nombre_archivo
        })

    return segmentos


def segmentar_video(
    video_id: str,
    video_path: str | Path,
    output_dir: str | Path,
    duracion_segmento_min: float = 12.0,
    recomprimir: bool = False
) -> Path:
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video fuente: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    plan = crear_plan_segmentos(
        video_id=video_id,
        video_path=video_path,
        duracion_segmento_min=duracion_segmento_min
    )

    for segmento in plan:
        salida = output_dir / segmento["archivo_salida"]

        if salida.exists():
            print(f"[SKIP] Ya existe: {salida}")
            continue

        if recomprimir:
            comando = [
                "ffmpeg",
                "-y",
                "-ss", segmento["inicio"],
                "-to", segmento["fin"],
                "-i", str(video_path),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                str(salida)
            ]
        else:
            comando = [
                "ffmpeg",
                "-y",
                "-ss", segmento["inicio"],
                "-to", segmento["fin"],
                "-i", str(video_path),
                "-c", "copy",
                str(salida)
            ]

        print(f"[INFO] Creando segmento: {salida.name}")
        ejecutar_comando(comando)

    plan_path = output_dir / f"{video_id}_segment_plan.json"
    with plan_path.open("w", encoding="utf-8") as f:
        json.dump({
            "video_id": video_id,
            "video_source": str(video_path),
            "output_dir": str(output_dir),
            "duracion_segmento_min": duracion_segmento_min,
            "recomprimir": recomprimir,
            "segmentos": plan
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Plan guardado en: {plan_path}")
    return plan_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Segmenta videos largos en bloques digeribles para análisis."
    )

    parser.add_argument(
        "--video-id",
        required=True,
        help="Identificador lógico del video. Ejemplo: V01"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Ruta del video fuente."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardarán los segmentos."
    )
    parser.add_argument(
        "--segment-min",
        type=float,
        default=12.0,
        help="Duración aproximada de cada segmento en minutos."
    )
    parser.add_argument(
        "--recompress",
        action="store_true",
        help="Recomprime los segmentos. Si no se usa, intenta cortar sin recomprimir."
    )

    args = parser.parse_args()

    try:
        segmentar_video(
            video_id=args.video_id,
            video_path=args.input,
            output_dir=args.output_dir,
            duracion_segmento_min=args.segment_min,
            recomprimir=args.recompress
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())