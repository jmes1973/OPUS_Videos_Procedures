from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json
import sys

from src.extraction.frames_indexer import crear_frames_index_desde_metadata
from src.analysis.event_detector import crear_events_raw_desde_frames_index
from src.analysis.timeline_builder import crear_timeline_raw_desde_events_raw
from src.analysis.step_normalizer import crear_steps_normalized_desde_timeline
from src.analysis.capture_selector import crear_capture_plan_desde_steps
from src.extraction.frame_extractor import extraer_y_generar_frames_metadata


def guardar_json(ruta: str | Path, contenido: dict) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def crear_run_id() -> str:
    return datetime.now().strftime("run_%Y%m%d_%H%M%S")


def crear_estructura_run(base_runs_dir: Path, run_id: str) -> Path:
    run_dir = base_runs_dir / run_id
    subdirs = [
        "frames",
        "frames_index",
        "events_raw",
        "timeline_raw",
        "steps_normalized",
        "capture_plan",
        "reports",
        "guides",
        "logs"
    ]

    for subdir in subdirs:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    return run_dir


def crear_run_manifest(
    run_dir: Path,
    run_id: str,
    source_video: str,
    frames_metadata_path: str
) -> None:
    manifest = {
        "run_id": run_id,
        "video_source": source_video,
        "frames_metadata_source": frames_metadata_path,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": "",
        "pipeline_version": "0.1.0",
        "status": "running"
    }
    guardar_json(run_dir / "run_manifest.json", manifest)


def actualizar_run_manifest_final(
    run_dir: Path,
    status: str
) -> None:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        return

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    manifest["status"] = status

    guardar_json(manifest_path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta el pipeline mínimo de análisis de video OPUS."
    )

    parser.add_argument("--video-id", required=True, help="Identificador lógico del video.")
    parser.add_argument("--source-video", required=True, help="Ruta del video fuente.")
    parser.add_argument("--frames-metadata", required=False, default="", help="Ruta al JSON de metadatos de frames.")
    parser.add_argument("--terminology", default="config/terminology.json", help="Ruta a terminology.json.")
    parser.add_argument("--action-lexicon", default="config/action_lexicon.json", help="Ruta a action_lexicon.json.")
    parser.add_argument("--runs-dir", default="runs", help="Carpeta base de corridas.")
    parser.add_argument("--target-fps", type=float, default=1.0, help="FPS objetivo usado en extracción previa.")
    parser.add_argument("--diff-threshold", type=float, default=0.0, help="Umbral de diferencia usado en extracción previa.")

    args = parser.parse_args()

    try:
        run_id = crear_run_id()
        runs_dir = Path(args.runs_dir)
        run_dir = crear_estructura_run(runs_dir, run_id)

        frames_metadata_path = args.frames_metadata

        if not frames_metadata_path:
            print("[INFO] Extrayendo frames desde video real ...")
            frames_metadata_path = str(
                extraer_y_generar_frames_metadata(
                    video_path=args.source_video,
                    run_dir=run_dir,
                    target_fps=args.target_fps
                )
            )        

        crear_run_manifest(
            run_dir=run_dir,
            run_id=run_id,
            source_video=args.source_video,
            frames_metadata_path=frames_metadata_path
        )

        frames_index_path = run_dir / "frames_index" / "frames_index.json"
        events_raw_path = run_dir / "events_raw" / "events_raw.json"
        timeline_raw_path = run_dir / "timeline_raw" / "timeline_raw.json"
        steps_normalized_path = run_dir / "steps_normalized" / "steps_normalized.json"
        capture_plan_path = run_dir / "capture_plan" / "capture_plan.json"

        extraction_config = {
            "mode": "metadata_precalculada",
            "target_fps": args.target_fps,
            "keyframe_detection": True,
            "diff_method": "precalculado",
            "diff_threshold": args.diff_threshold,
            "save_format": "jpg"
        }

        print(f"[INFO] Iniciando corrida: {run_id}")
        print("[INFO] Construyendo frames_index.json ...")

        crear_frames_index_desde_metadata(
            video_id=args.video_id,
            run_id=run_id,
            source_video=args.source_video,
            frames_metadata_path=frames_metadata_path,
            terminology_path=args.terminology,
            output_path=frames_index_path,
            extraction_config=extraction_config
        )

        print("[INFO] Construyendo events_raw.json ...")

        crear_events_raw_desde_frames_index(
            frames_index_path=frames_index_path,
            action_lexicon_path=args.action_lexicon,
            terminology_path=args.terminology,
            output_path=events_raw_path
        )

        print("[INFO] Construyendo timeline_raw.json ...")

        crear_timeline_raw_desde_events_raw(
            events_raw_path=events_raw_path,
            output_path=timeline_raw_path
        )

        print("[INFO] Construyendo steps_normalized.json ...")

        crear_steps_normalized_desde_timeline(
            timeline_raw_path=timeline_raw_path,
            events_raw_path=events_raw_path,
            terminology_path=args.terminology,
            output_path=steps_normalized_path
        )

        print("[INFO] Construyendo capture_plan.json ...")

        crear_capture_plan_desde_steps(
            steps_normalized_path=steps_normalized_path,
            frames_index_path=frames_index_path,
            output_path=capture_plan_path
        )

        actualizar_run_manifest_final(run_dir=run_dir, status="completed")

        print("[OK] Pipeline completado correctamente.")
        print(f"[OK] Resultados en: {run_dir}")

        return 0

    except Exception as e:
        print(f"[ERROR] El pipeline falló: {e}", file=sys.stderr)

        try:
            if "run_dir" in locals():
                actualizar_run_manifest_final(run_dir=run_dir, status="failed")
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
