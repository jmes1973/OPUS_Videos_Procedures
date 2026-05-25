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


def construir_prompt_consolidacion(video_id: str, informes_segmentos: list[dict[str, str]]) -> str:
    bloques = []

    for item in informes_segmentos:
        bloques.append(
            f"""
==============================
SEGMENTO: {item["segmento_id"]}
ARCHIVO: {item["archivo"]}
==============================

{item["contenido"]}
""".strip()
        )

    contenido_segmentos = "\n\n\n".join(bloques)

    return f"""
Actúa como editor técnico, pedagógico y documental.

Vas a consolidar varios informes preliminares de segmentos pertenecientes a un mismo video.

Tu tarea es crear un informe único del video completo.

No hagas un resumen ejecutivo.
No elimines información técnica relevante.
No inventes información.
No afirmes información visual si no está confirmada en los informes fuente.
Conserva el máximo detalle posible.
Si hay redundancias, consolídalas sin borrar matices importantes.
Si hay dudas o información no verificable, consérvala en una sección específica.

Video: {video_id}

Estructura obligatoria del informe consolidado:

# Informe consolidado del video {video_id}

## 1. Identificación general
Indica que este informe se construye a partir de informes preliminares por segmento.

## 2. Estructura de segmentos analizados
Crea una tabla con:
| Segmento | Archivo fuente | Contenido principal | Observaciones |

## 3. Desarrollo detallado del contenido del video
Organiza todo el contenido por bloques temáticos.
No reduzcas excesivamente la información.

## 4. Línea de tiempo consolidada
Crea una tabla con:
| Segmento | Tiempo / referencia | Contenido tratado | Conceptos | Observaciones |

## 5. Conceptos consolidados y definiciones
Crea una tabla con:
| Concepto | Definición detallada | Segmentos donde aparece | Importancia | Relación con otros conceptos |

## 6. Atajos de teclado consolidados
Crea una tabla con:
| Atajo | Función | Segmentos donde aparece | Confirmación | Observaciones |

Si no se identifican atajos, indícalo claramente.

## 7. Herramientas, menús, botones o comandos consolidados
Crea una tabla con:
| Elemento | Función | Segmentos donde aparece | Contexto de uso | Observaciones |

## 8. Procedimientos paso a paso
Consolida todos los procedimientos mencionados o inferidos.
Para cada procedimiento usa:

### Procedimiento: [nombre]
**Objetivo:**
**Pasos:**
**Resultado esperado:**
**Segmentos relacionados:**
**Dudas o confirmaciones necesarias:**

## 9. Glosario técnico del video
Crea una tabla alfabética con:
| Término | Definición | Segmentos relacionados |

## 10. Información que requiere confirmación visual
Lista todo lo que debería verificarse con frames o con el video original.

## 11. Material reutilizable
Organiza elementos que pueden reutilizarse en:
- manual técnico;
- curso;
- guion educativo;
- glosario;
- lista de comandos;
- checklist de procedimiento.

## 12. Control de calidad del informe
Indica:
- posibles vacíos;
- redundancias detectadas;
- contradicciones;
- partes débiles por falta de análisis visual;
- partes que conviene revisar con ChatGPT Plus.

Reglas:
- Mantén lenguaje técnico claro.
- Usa tablas donde sea útil.
- No conviertas el informe en resumen.
- Conserva la trazabilidad por segmento.
- Diferencia confirmado, inferido y pendiente de confirmar.

Informes preliminares por segmento:

{contenido_segmentos}
""".strip()


def recolectar_informes_segmento(input_dir: str | Path) -> list[dict[str, str]]:
    input_dir = Path(input_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de informes: {input_dir}")

    archivos = sorted(input_dir.glob("*_informe_preliminar.md"))

    if not archivos:
        raise FileNotFoundError(f"No se encontraron informes preliminares en: {input_dir}")

    informes: list[dict[str, str]] = []

    for archivo in archivos:
        segmento_id = archivo.name.replace("_informe_preliminar.md", "")
        informes.append({
            "segmento_id": segmento_id,
            "archivo": str(archivo),
            "contenido": cargar_texto(archivo)
        })

    return informes


def consolidar_video(
    video_id: str,
    input_dir: str | Path,
    output_path: str | Path,
    model: str = "llama3.1:8b",
    temperature: float = 0.2
) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    informes = recolectar_informes_segmento(input_dir)

    prompt = construir_prompt_consolidacion(
        video_id=video_id,
        informes_segmentos=informes
    )

    print(f"[INFO] Consolidando video {video_id} con Ollama...")
    print(f"[INFO] Segmentos incluidos: {len(informes)}")

    informe_consolidado = generar_con_ollama(
        prompt=prompt,
        model=model,
        temperature=temperature
    )

    guardar_texto(output_path, informe_consolidado)

    manifest_path = output_path.with_suffix(".manifest.json")

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "video_id": video_id,
            "input_dir": str(input_dir),
            "output_path": str(output_path),
            "model": model,
            "temperature": temperature,
            "total_segmentos": len(informes),
            "segmentos": [
                {
                    "segmento_id": item["segmento_id"],
                    "archivo": item["archivo"]
                }
                for item in informes
            ]
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Informe consolidado guardado en: {output_path}")
    print(f"[OK] Manifest guardado en: {manifest_path}")

    return {
        "video_id": video_id,
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "total_segmentos": len(informes)
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolida informes preliminares por segmento en un informe único por video."
    )

    parser.add_argument(
        "--video-id",
        required=True,
        help="Identificador lógico del video. Ejemplo: V01"
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta donde están los informes preliminares por segmento."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Ruta del informe consolidado de salida."
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
        consolidar_video(
            video_id=args.video_id,
            input_dir=args.input_dir,
            output_path=args.output,
            model=args.model,
            temperature=args.temperature
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())