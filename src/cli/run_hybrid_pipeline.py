from __future__ import annotations

from pathlib import Path
import argparse
import json
from datetime import datetime
from typing import Any

from src.preprocess.segment_video import segmentar_video
from src.audio.extract_audio import extraer_audio_desde_carpeta
from src.audio.transcribe_whisper import transcribir_carpeta
from src.llm.analyze_transcripts import analizar_carpeta
from src.reports.consolidate_video_report import consolidar_video


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def crear_rutas_workspace(workspace: str | Path, video_id: str) -> dict[str, Path]:
    workspace = Path(workspace)

    return {
        "workspace": workspace,
        "segmentos": workspace / "01_segmentos" / video_id,
        "audio": workspace / "02_audio" / video_id,
        "transcripciones": workspace / "03_transcripciones" / video_id,
        "informes_ollama": workspace / "05_informes_segmento_ollama" / video_id,
        "informes_video": workspace / "07_informes_video",
        "logs": workspace / "99_logs" / video_id,
    }


def ejecutar_pipeline_hibrido(
    video_id: str,
    input_video: str | Path,
    workspace: str | Path,
    segment_min: float = 12.0,
    min_last_segment_min: float = 3.0,
    recompress_segments: bool = False,
    whisper_model: str = "small",
    whisper_language: str = "es",
    whisper_device: str = "cpu",
    whisper_compute_type: str = "int8",
    ollama_model: str = "llama3.1:8b",
    ollama_temperature: float = 0.2,
    skip_segmentation: bool = False,
    skip_audio: bool = False,
    skip_transcription: bool = False,
    skip_ollama_analysis: bool = False,
    skip_consolidation: bool = False,
) -> Path:
    input_video = Path(input_video)
    rutas = crear_rutas_workspace(workspace, video_id)

    if not input_video.exists():
        raise FileNotFoundError(f"No existe el video fuente: {input_video}")

    started_at = datetime.now().isoformat(timespec="seconds")

    manifest: dict[str, Any] = {
        "video_id": video_id,
        "input_video": str(input_video),
        "workspace": str(Path(workspace)),
        "started_at": started_at,
        "finished_at": "",
        "status": "running",
        "steps": [],
        "config": {
            "segment_min": segment_min,
            "min_last_segment_min": min_last_segment_min,
            "recompress_segments": recompress_segments,
            "whisper_model": whisper_model,
            "whisper_language": whisper_language,
            "whisper_device": whisper_device,
            "whisper_compute_type": whisper_compute_type,
            "ollama_model": ollama_model,
            "ollama_temperature": ollama_temperature,
        },
        "outputs": {},
    }

    rutas["logs"].mkdir(parents=True, exist_ok=True)
    pipeline_manifest_path = rutas["logs"] / f"{video_id}_hybrid_pipeline_manifest.json"

    try:
        print("=" * 80)
        print(f"[PIPELINE] Iniciando pipeline híbrido para {video_id}")
        print("=" * 80)

        if not skip_segmentation:
            print("[STEP 1] Segmentando video...")
            plan_path = segmentar_video(
                video_id=video_id,
                video_path=input_video,
                output_dir=rutas["segmentos"],
                duracion_segmento_min=segment_min,
                min_ultimo_segmento_min=min_last_segment_min,
                recomprimir=recompress_segments,
            )
            manifest["steps"].append({"step": "segmentation", "status": "completed"})
            manifest["outputs"]["segment_plan"] = str(plan_path)
        else:
            print("[SKIP] Segmentación omitida.")
            manifest["steps"].append({"step": "segmentation", "status": "skipped"})

        if not skip_audio:
            print("[STEP 2] Extrayendo audio WAV...")
            audio_manifest = extraer_audio_desde_carpeta(
                input_dir=rutas["segmentos"],
                output_dir=rutas["audio"],
                sample_rate=16000,
            )
            manifest["steps"].append({"step": "audio_extraction", "status": "completed"})
            manifest["outputs"]["audio_manifest"] = str(audio_manifest)
        else:
            print("[SKIP] Extracción de audio omitida.")
            manifest["steps"].append({"step": "audio_extraction", "status": "skipped"})

        if not skip_transcription:
            print("[STEP 3] Transcribiendo con faster-whisper...")
            transcription_manifest = transcribir_carpeta(
                input_dir=rutas["audio"],
                output_dir=rutas["transcripciones"],
                model_size=whisper_model,
                language=whisper_language,
                device=whisper_device,
                compute_type=whisper_compute_type,
            )
            manifest["steps"].append({"step": "transcription", "status": "completed"})
            manifest["outputs"]["transcription_manifest"] = str(transcription_manifest)
        else:
            print("[SKIP] Transcripción omitida.")
            manifest["steps"].append({"step": "transcription", "status": "skipped"})

        if not skip_ollama_analysis:
            print("[STEP 4] Analizando transcripciones con Ollama...")
            analysis_manifest = analizar_carpeta(
                input_dir=rutas["transcripciones"],
                output_dir=rutas["informes_ollama"],
                model=ollama_model,
                temperature=ollama_temperature,
            )
            manifest["steps"].append({"step": "ollama_analysis", "status": "completed"})
            manifest["outputs"]["analysis_manifest"] = str(analysis_manifest)
        else:
            print("[SKIP] Análisis con Ollama omitido.")
            manifest["steps"].append({"step": "ollama_analysis", "status": "skipped"})

        if not skip_consolidation:
            print("[STEP 5] Consolidando informe por video...")
            output_report = rutas["informes_video"] / f"{video_id}_informe_consolidado.md"
            consolidation_result = consolidar_video(
                video_id=video_id,
                input_dir=rutas["informes_ollama"],
                output_path=output_report,
                model=ollama_model,
                temperature=ollama_temperature,
            )
            manifest["steps"].append({"step": "video_consolidation", "status": "completed"})
            manifest["outputs"]["video_report"] = consolidation_result["output_path"]
            manifest["outputs"]["video_report_manifest"] = consolidation_result["manifest_path"]
        else:
            print("[SKIP] Consolidación omitida.")
            manifest["steps"].append({"step": "video_consolidation", "status": "skipped"})

        manifest["status"] = "completed"
        manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
        guardar_json(pipeline_manifest_path, manifest)

        print("=" * 80)
        print("[OK] Pipeline híbrido completado.")
        print(f"[OK] Manifest: {pipeline_manifest_path}")
        print("=" * 80)

        return pipeline_manifest_path

    except Exception as e:
        manifest["status"] = "failed"
        manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
        manifest["error"] = str(e)
        guardar_json(pipeline_manifest_path, manifest)

        print("=" * 80)
        print(f"[ERROR] Pipeline falló: {e}")
        print(f"[ERROR] Manifest de fallo: {pipeline_manifest_path}")
        print("=" * 80)

        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline híbrido completo: segmentación, audio, transcripción, análisis y consolidación."
    )

    parser.add_argument(
        "--video-id",
        required=True,
        help="Identificador lógico del video. Ejemplo: V01, V02, V03."
    )
    parser.add_argument(
        "--input-video",
        required=True,
        help="Ruta del video fuente."
    )
    parser.add_argument(
        "--workspace",
        default=r"C:\OPUS_VIDEO_ANALYSIS",
        help="Carpeta base de trabajo. Por defecto: C:\\OPUS_VIDEO_ANALYSIS"
    )
    parser.add_argument(
        "--segment-min",
        type=float,
        default=12.0,
        help="Duración aproximada de cada segmento en minutos."
    )
    parser.add_argument(
        "--min-last-segment-min",
        type=float,
        default=3.0,
        help="Duración mínima del último segmento. Si es menor, se fusiona con el anterior."
    )
    parser.add_argument(
        "--recompress-segments",
        action="store_true",
        help="Recomprime los segmentos. Si no se usa, intenta cortar sin recomprimir."
    )
    parser.add_argument(
        "--whisper-model",
        default="small",
        help="Modelo Whisper. Ejemplos: tiny, base, small, medium, large-v3."
    )
    parser.add_argument(
        "--whisper-language",
        default="es",
        help="Idioma del audio. Por defecto: es."
    )
    parser.add_argument(
        "--whisper-device",
        default="cpu",
        help="Dispositivo para Whisper: cpu o cuda."
    )
    parser.add_argument(
        "--whisper-compute-type",
        default="int8",
        help="Tipo de cómputo para Whisper. CPU: int8. GPU: int8_float16."
    )
    parser.add_argument(
        "--ollama-model",
        default="llama3.1:8b",
        help="Modelo de Ollama. Ejemplo: llama3.1:8b, qwen3:14b."
    )
    parser.add_argument(
        "--ollama-temperature",
        type=float,
        default=0.2,
        help="Temperatura del modelo Ollama."
    )

    parser.add_argument("--skip-segmentation", action="store_true")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--skip-transcription", action="store_true")
    parser.add_argument("--skip-ollama-analysis", action="store_true")
    parser.add_argument("--skip-consolidation", action="store_true")

    args = parser.parse_args()

    try:
        ejecutar_pipeline_hibrido(
            video_id=args.video_id,
            input_video=args.input_video,
            workspace=args.workspace,
            segment_min=args.segment_min,
            min_last_segment_min=args.min_last_segment_min,
            recompress_segments=args.recompress_segments,
            whisper_model=args.whisper_model,
            whisper_language=args.whisper_language,
            whisper_device=args.whisper_device,
            whisper_compute_type=args.whisper_compute_type,
            ollama_model=args.ollama_model,
            ollama_temperature=args.ollama_temperature,
            skip_segmentation=args.skip_segmentation,
            skip_audio=args.skip_audio,
            skip_transcription=args.skip_transcription,
            skip_ollama_analysis=args.skip_ollama_analysis,
            skip_consolidation=args.skip_consolidation,
        )
        return 0

    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())