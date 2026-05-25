from __future__ import annotations

from pathlib import Path
import argparse
import json
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


def extraer_audio_segmento(
    input_video: str | Path,
    output_audio: str | Path,
    sample_rate: int = 16000
) -> dict[str, Any]:
    input_video = Path(input_video)
    output_audio = Path(output_audio)

    if not input_video.exists():
        raise FileNotFoundError(f"No existe el video de entrada: {input_video}")

    output_audio.parent.mkdir(parents=True, exist_ok=True)

    comando = [
        "ffmpeg",
        "-y",
        "-i", str(input_video),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(output_audio)
    ]

    print(f"[INFO] Extrayendo audio: {input_video.name}")
    ejecutar_comando(comando)

    return {
        "input_video": str(input_video),
        "output_audio": str(output_audio),
        "sample_rate": sample_rate,
        "channels": 1,
        "codec": "pcm_s16le",
        "format": "wav"
    }


def extraer_audio_desde_carpeta(
    input_dir: str | Path,
    output_dir: str | Path,
    sample_rate: int = 16000
) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de segmentos: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(input_dir.glob("*.mp4"))

    if not videos:
        raise FileNotFoundError(f"No se encontraron archivos .mp4 en: {input_dir}")

    resultados: list[dict[str, Any]] = []

    for video in videos:
        output_audio = output_dir / f"{video.stem}.wav"

        if output_audio.exists():
            print(f"[SKIP] Ya existe: {output_audio.name}")
            resultados.append({
                "input_video": str(video),
                "output_audio": str(output_audio),
                "status": "skipped_existing"
            })
            continue

        resultado = extraer_audio_segmento(
            input_video=video,
            output_audio=output_audio,
            sample_rate=sample_rate
        )
        resultado["status"] = "created"
        resultados.append(resultado)

    manifest_path = output_dir / "audio_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "sample_rate": sample_rate,
            "total_videos": len(videos),
            "total_audios": len(resultados),
            "audios": resultados
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Manifest de audio guardado en: {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrae audio WAV mono 16 kHz desde segmentos de video."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta donde están los segmentos .mp4."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardarán los audios .wav."
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Frecuencia de muestreo del audio. Por defecto: 16000 Hz."
    )

    args = parser.parse_args()

    try:
        extraer_audio_desde_carpeta(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            sample_rate=args.sample_rate
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())