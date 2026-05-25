from __future__ import annotations

from pathlib import Path
import argparse
import json
from typing import Any

from src.llm.ollama_client import generar_con_ollama


def cargar_texto(ruta: str | Path) -> str:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return f.read()


def guardar_texto(ruta: str | Path, contenido: str) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        f.write(contenido)


def construir_prompt_analisis(segmento_id: str, transcripcion: str) -> str:
    return f"""
Actúa como analista técnico, pedagógico y editorial de videos educativos.

Vas a analizar la transcripción de un segmento de video.

No hagas un resumen.

Tu tarea es extraer y desarrollar todo el contenido útil para documentación técnica, capacitación y creación de informes.

Diferencia claramente:
- lo dicho en el audio;
- lo inferido;
- lo que requiere confirmación visual;
- lo que no puede verificarse solo con la transcripción.

Segmento: {segmento_id}

Estructura obligatoria del informe:

# Informe preliminar del segmento {segmento_id}

## 1. Identificación del segmento
Indica el identificador del segmento y el tipo de información disponible.

## 2. Análisis detallado del audio
Desarrolla las ideas explicadas en la transcripción sin resumirlas excesivamente.

## 3. Línea de tiempo basada en la transcripción
Crea una tabla con:
| Tiempo | Contenido hablado | Concepto tratado | Observaciones |

## 4. Conceptos detectados y definiciones
Crea una tabla con:
| Concepto | Definición detallada | Cómo aparece en el segmento | Importancia |

Incluye conceptos explícitos e implícitos.

## 5. Atajos de teclado mencionados
Crea una tabla con:
| Atajo | Función | Contexto | Confirmación |

Si no hay atajos, escribe: No se identifican atajos de teclado en la transcripción.

## 6. Herramientas, menús, botones o comandos mencionados
Crea una tabla con:
| Elemento | Función | Contexto de uso | Observaciones |

## 7. Procedimientos paso a paso
Extrae cualquier procedimiento explicado o sugerido en la transcripción.

## 8. Dudas o información que requiere confirmación visual
Lista lo que debería verificarse mirando el video o frames.

## 9. Material reutilizable
Incluye posibles elementos útiles para:
- manual técnico;
- curso;
- guion educativo;
- glosario;
- lista de comandos.

Reglas:
- No inventes información.
- No afirmes que algo se ve en pantalla si solo aparece en la transcripción.
- Conserva detalle.
- Usa lenguaje técnico claro.
- No hagas resumen ejecutivo.

Transcripción del segmento:

{transcripcion}
""".strip()


def analizar_transcripcion(
    transcript_path: str | Path,
    output_dir: str | Path,
    model: str = "llama3.1:8b",
    temperature: float = 0.2
) -> dict[str, Any]:
    transcript_path = Path(transcript_path)
    output_dir = Path(output_dir)

    if not transcript_path.exists():
        raise FileNotFoundError(f"No existe la transcripción: {transcript_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    segmento_id = transcript_path.stem
    output_path = output_dir / f"{segmento_id}_informe_preliminar.md"

    if output_path.exists():
        print(f"[SKIP] Ya existe informe preliminar: {output_path.name}")
        return {
            "segmento_id": segmento_id,
            "transcript_path": str(transcript_path),
            "output_path": str(output_path),
            "model": model,
            "status": "skipped_existing"
        }

    transcripcion = cargar_texto(transcript_path)

    prompt = construir_prompt_analisis(
        segmento_id=segmento_id,
        transcripcion=transcripcion
    )

    print(f"[INFO] Analizando con Ollama: {segmento_id}")
    informe = generar_con_ollama(
        prompt=prompt,
        model=model,
        temperature=temperature
    )

    guardar_texto(output_path, informe)

    return {
        "segmento_id": segmento_id,
        "transcript_path": str(transcript_path),
        "output_path": str(output_path),
        "model": model,
        "status": "created"
    }


def analizar_carpeta(
    input_dir: str | Path,
    output_dir: str | Path,
    model: str = "llama3.1:8b",
    temperature: float = 0.2
) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de transcripciones: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    transcripciones = sorted(input_dir.glob("*.txt"))

    if not transcripciones:
        raise FileNotFoundError(f"No se encontraron archivos .txt en: {input_dir}")

    resultados: list[dict[str, Any]] = []

    for transcript_path in transcripciones:
        resultado = analizar_transcripcion(
            transcript_path=transcript_path,
            output_dir=output_dir,
            model=model,
            temperature=temperature
        )
        resultados.append(resultado)

    manifest_path = output_dir / "analysis_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "model": model,
            "temperature": temperature,
            "total_transcripciones": len(transcripciones),
            "analisis": resultados
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Manifest de análisis guardado en: {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analiza transcripciones de segmentos usando Ollama."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta donde están las transcripciones .txt."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardarán los informes preliminares."
    )
    parser.add_argument(
        "--model",
        default="llama3.1:8b",
        help="Modelo de Ollama. Ejemplo: llama3.1:8b, qwen3:14b."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperatura del modelo."
    )

    args = parser.parse_args()

    try:
        analizar_carpeta(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model=args.model,
            temperature=args.temperature
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())