from __future__ import annotations

from pathlib import Path
import argparse
import json
from typing import Any

from faster_whisper import WhisperModel


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def transcribir_audio(
    audio_path: str | Path,
    output_dir: str | Path,
    model_size: str = "small",
    language: str = "es",
    device: str = "cuda",
    compute_type: str = "int8_float16"
) -> dict[str, Any]:
    audio_path = Path(audio_path)
    output_dir = Path(output_dir)

    if not audio_path.exists():
        raise FileNotFoundError(f"No existe el audio: {audio_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = audio_path.stem

    txt_path = output_dir / f"{base_name}.txt"
    srt_path = output_dir / f"{base_name}.srt"
    json_path = output_dir / f"{base_name}.json"

    print(f"[INFO] Cargando modelo Whisper: {model_size}")
    model = WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type
    )

    print(f"[INFO] Transcribiendo: {audio_path.name}")
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=5
    )

    all_segments: list[dict[str, Any]] = []

    with txt_path.open("w", encoding="utf-8") as txt, srt_path.open("w", encoding="utf-8") as srt:
        for i, segment in enumerate(segments, start=1):
            text = segment.text.strip()

            txt.write(f"[{segment.start:.2f} - {segment.end:.2f}] {text}\n")

            srt.write(f"{i}\n")
            srt.write(f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n")
            srt.write(f"{text}\n\n")

            all_segments.append({
                "index": i,
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "text": text
            })

    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "audio_file": str(audio_path),
            "model_size": model_size,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": all_segments
        }, f, ensure_ascii=False, indent=2)

    return {
        "audio_file": str(audio_path),
        "txt": str(txt_path),
        "srt": str(srt_path),
        "json": str(json_path),
        "segments": len(all_segments)
    }


def transcribir_carpeta(
    input_dir: str | Path,
    output_dir: str | Path,
    model_size: str = "small",
    language: str = "es",
    device: str = "cuda",
    compute_type: str = "int8_float16"
) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de audio: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    audios = sorted(input_dir.glob("*.wav"))

    if not audios:
        raise FileNotFoundError(f"No se encontraron archivos .wav en: {input_dir}")

    resultados: list[dict[str, Any]] = []

    for audio in audios:
        resultado = transcribir_audio(
            audio_path=audio,
            output_dir=output_dir,
            model_size=model_size,
            language=language,
            device=device,
            compute_type=compute_type
        )
        resultados.append(resultado)

    manifest_path = output_dir / "transcription_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "model_size": model_size,
            "language": language,
            "device": device,
            "compute_type": compute_type,
            "total_audios": len(audios),
            "transcriptions": resultados
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Manifest de transcripción guardado en: {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audios WAV usando faster-whisper."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta donde están los audios .wav."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardarán las transcripciones."
    )
    parser.add_argument(
        "--model-size",
        default="small",
        help="Modelo Whisper. Ejemplos: tiny, base, small, medium, large-v3."
    )
    parser.add_argument(
        "--language",
        default="es",
        help="Idioma del audio. Por defecto: es."
    )
    parser.add_argument(
        "--device",
        default="cuda",
        help="Dispositivo: cuda o cpu."
    )
    parser.add_argument(
        "--compute-type",
        default="int8_float16",
        help="Tipo de cómputo. Para GPU: int8_float16. Para CPU: int8."
    )

    args = parser.parse_args()

    try:
        transcribir_carpeta(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model_size=args.model_size,
            language=args.language,
            device=args.device,
            compute_type=args.compute_type
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())