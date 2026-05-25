from __future__ import annotations

from pathlib import Path
import argparse
import json
import math
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


def dividir_en_bloques(items: list[Path], chunk_size: int) -> list[list[Path]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def construir_prompt_parcial(video_id: str, bloque_num: int, archivos: list[Path]) -> str:
    bloques_texto = []

    for archivo in archivos:
        segmento_id = archivo.name.replace("_informe_preliminar.md", "")
        contenido = cargar_texto(archivo)

        bloques_texto.append(
            f"""
==============================
SEGMENTO: {segmento_id}
ARCHIVO: {archivo.name}
==============================

{contenido}
""".strip()
        )

    contenido_bloque = "\n\n\n".join(bloques_texto)

    return f"""
Actúa como editor técnico y documental.

Vas a consolidar un bloque parcial de informes preliminares pertenecientes al video {video_id}.

Este es el bloque parcial número {bloque_num}.

No hagas un resumen ejecutivo.
No elimines información técnica relevante.
No inventes información.
Conserva trazabilidad por segmento.
Si hay información dudosa o pendiente de confirmación visual, consérvala.

Estructura obligatoria:

# Consolidado parcial {bloque_num} del video {video_id}

## 1. Segmentos incluidos
Crea una tabla con:
| Segmento | Archivo | Contenido principal | Observaciones |

## 2. Desarrollo técnico del bloque
Organiza el contenido por temas y conserva detalle.

## 3. Línea de tiempo parcial
Crea una tabla con:
| Segmento | Referencia temporal | Contenido tratado | Conceptos | Observaciones |

## 4. Conceptos y definiciones del bloque
Crea una tabla con:
| Concepto | Definición | Segmentos donde aparece | Importancia |

## 5. Herramientas, comandos, botones o atajos
Crea una tabla con:
| Elemento | Función | Segmento | Observaciones |

## 6. Procedimientos detectados
Lista procedimientos paso a paso si aparecen.

## 7. Información pendiente de confirmación visual
Lista dudas, inferencias o aspectos no verificables.

Informes del bloque:

{contenido_bloque}
""".strip()


def construir_prompt_final(video_id: str, parciales: list[Path]) -> str:
    bloques_texto = []

    for archivo in parciales:
        contenido = cargar_texto(archivo)
        bloques_texto.append(
            f"""
==============================
CONSOLIDADO PARCIAL: {archivo.name}
==============================

{contenido}
""".strip()
        )

    contenido_parciales = "\n\n\n".join(bloques_texto)

    return f"""
Actúa como editor técnico maestro.

Vas a crear el informe consolidado final del video {video_id} a partir de varios consolidados parciales.

No hagas un resumen ejecutivo.
No elimines información técnica relevante.
Une redundancias sin perder matices.
Conserva trazabilidad por segmento cuando sea posible.
No inventes información.
Diferencia confirmado, inferido y pendiente de confirmación visual.

Estructura obligatoria:

# Informe consolidado del video {video_id}

## 1. Identificación general
Indica que este informe fue generado a partir de consolidados parciales.

## 2. Estructura de segmentos y bloques
Crea una tabla con:
| Bloque parcial | Segmentos incluidos | Contenido principal | Observaciones |

## 3. Desarrollo detallado del contenido del video
Organiza el contenido por bloques temáticos, sin reducirlo excesivamente.

## 4. Línea de tiempo consolidada
Crea una tabla con:
| Segmento / bloque | Referencia temporal | Contenido tratado | Conceptos | Observaciones |

## 5. Conceptos consolidados y definiciones
Crea una tabla con:
| Concepto | Definición detallada | Segmentos o bloques donde aparece | Importancia | Relación con otros conceptos |

## 6. Atajos de teclado consolidados
Crea una tabla con:
| Atajo | Función | Segmentos o bloques donde aparece | Confirmación | Observaciones |

Si no hay atajos, indícalo claramente.

## 7. Herramientas, menús, botones o comandos consolidados
Crea una tabla con:
| Elemento | Función | Segmentos o bloques donde aparece | Contexto de uso | Observaciones |

## 8. Procedimientos paso a paso
Consolida procedimientos detectados.

## 9. Glosario técnico del video
Crea una tabla alfabética con:
| Término | Definición | Segmentos o bloques relacionados |

## 10. Información que requiere confirmación visual
Lista todo lo que debería verificarse con frames o con el video original.

## 11. Material reutilizable
Organiza elementos reutilizables para:
- manual técnico;
- curso;
- guion educativo;
- glosario;
- lista de comandos;
- checklist de procedimiento.

## 12. Control de calidad
Indica vacíos, redundancias, contradicciones, partes débiles y aspectos que conviene revisar con ChatGPT Plus.

Consolidados parciales:

{contenido_parciales}
""".strip()


def consolidar_video_por_bloques(
    video_id: str,
    input_dir: str | Path,
    output_dir: str | Path,
    chunk_size: int = 2,
    model: str = "gemma3n:e2b",
    temperature: float = 0.2
) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de informes: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    informes = sorted(input_dir.glob("*_informe_preliminar.md"))

    if not informes:
        raise FileNotFoundError(f"No se encontraron informes preliminares en: {input_dir}")

    bloques = dividir_en_bloques(informes, chunk_size)
    parciales_dir = output_dir / f"{video_id}_parciales"
    parciales_dir.mkdir(parents=True, exist_ok=True)

    parciales_generados: list[Path] = []

    for i, bloque in enumerate(bloques, start=1):
        parcial_path = parciales_dir / f"{video_id}_parcial_{i:02d}.md"

        if parcial_path.exists():
            print(f"[SKIP] Ya existe consolidado parcial: {parcial_path.name}")
            parciales_generados.append(parcial_path)
            continue

        print(f"[INFO] Consolidando bloque parcial {i}/{len(bloques)} con {len(bloque)} segmento(s)...")

        prompt = construir_prompt_parcial(
            video_id=video_id,
            bloque_num=i,
            archivos=bloque
        )

        parcial = generar_con_ollama(
            prompt=prompt,
            model=model,
            temperature=temperature
        )

        guardar_texto(parcial_path, parcial)
        parciales_generados.append(parcial_path)

        print(f"[OK] Parcial guardado: {parcial_path}")

    final_path = output_dir / f"{video_id}_informe_consolidado.md"

    print(f"[INFO] Consolidando informe final desde {len(parciales_generados)} parciales...")

    prompt_final = construir_prompt_final(
        video_id=video_id,
        parciales=parciales_generados
    )

    informe_final = generar_con_ollama(
        prompt=prompt_final,
        model=model,
        temperature=temperature
    )

    guardar_texto(final_path, informe_final)

    manifest_path = output_dir / f"{video_id}_informe_consolidado_chunked.manifest.json"

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "video_id": video_id,
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "chunk_size": chunk_size,
            "model": model,
            "temperature": temperature,
            "total_informes_segmento": len(informes),
            "total_parciales": len(parciales_generados),
            "parciales": [str(p) for p in parciales_generados],
            "final_report": str(final_path)
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Informe final guardado en: {final_path}")
    print(f"[OK] Manifest guardado en: {manifest_path}")

    return {
        "video_id": video_id,
        "final_report": str(final_path),
        "manifest": str(manifest_path),
        "total_parciales": len(parciales_generados)
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolida informes por video usando bloques parciales para evitar timeouts."
    )

    parser.add_argument("--video-id", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--chunk-size", type=int, default=2)
    parser.add_argument("--model", default="gemma3n:e2b")
    parser.add_argument("--temperature", type=float, default=0.2)

    args = parser.parse_args()

    try:
        consolidar_video_por_bloques(
            video_id=args.video_id,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            chunk_size=args.chunk_size,
            model=args.model,
            temperature=args.temperature
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())