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


def recolectar_informes_video(input_dir: str | Path) -> list[Path]:
    input_dir = Path(input_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de informes: {input_dir}")

    archivos = sorted(input_dir.glob("V*_informe_consolidado.md"))

    if not archivos:
        raise FileNotFoundError(f"No se encontraron informes consolidados en: {input_dir}")

    return archivos


def construir_prompt_maestro(archivos: list[Path]) -> str:
    bloques = []

    for archivo in archivos:
        video_id = archivo.name.replace("_informe_consolidado.md", "")
        contenido = cargar_texto(archivo)

        bloques.append(
            f"""
==============================
VIDEO: {video_id}
ARCHIVO: {archivo.name}
==============================

{contenido}
""".strip()
        )

    contenido_global = "\n\n\n".join(bloques)

    return f"""
Actúa como editor técnico maestro especializado en documentación de software médico, simulación ecográfica y formación de usuarios.

Vas a construir un informe maestro global a partir de varios informes consolidados de videos.

Este informe pertenece a la primera capa documental del proyecto. Su objetivo no es ser todavía el manual definitivo, sino organizar toda la información textual extraída de los videos para preparar una futura guía de usuario completa de Volutracer OPUS.

No hagas un resumen ejecutivo.
No elimines información técnica relevante.
No inventes información.
Conserva trazabilidad por video.
Diferencia información confirmada, inferida y pendiente de confirmación visual.
Corrige terminología obvia cuando corresponda, especialmente:
- Volutracer OPUS
- Voluson
- GE Healthcare
- DICOM
- ecografía
- ultrasonido
- transductor
- volumen
- frame
- cine
- MPR
- STIC

Estructura obligatoria:

# Informe maestro global — Primera capa documental

## 1. Identificación general del proyecto
Explica que este documento integra informes consolidados de varios videos analizados mediante segmentación, transcripción y análisis preliminar con IA local.

## 2. Videos incluidos
Crea una tabla:
| Video | Archivo fuente | Contenido principal identificado | Observaciones |

## 3. Mapa general de contenidos
Organiza los temas principales detectados en todos los videos.

## 4. Desarrollo detallado por video
Para cada video, desarrolla:
### Video VXX
- Contenido principal
- Conceptos tratados
- Procedimientos mencionados
- Herramientas o funciones relevantes
- Dudas o puntos que requieren revisión visual

## 5. Conceptos técnicos consolidados
Crea una tabla:
| Concepto | Definición desarrollada | Videos donde aparece | Importancia para el manual | Observaciones terminológicas |

## 6. Procedimientos consolidados
Crea procedimientos completos usando esta estructura:

### Procedimiento: [nombre]
**Objetivo:**
**Descripción técnica:**
**Pasos documentados:**
**Videos relacionados:**
**Información pendiente de confirmación visual:**

## 7. Herramientas, menús, botones, comandos y funciones
Crea una tabla:
| Elemento | Función | Videos donde aparece | Contexto de uso | Confirmación pendiente |

## 8. Atajos de teclado
Crea una tabla:
| Atajo | Función | Videos donde aparece | Confirmación | Observaciones |

Si no se identifican atajos, indícalo claramente.

## 9. Glosario técnico preliminar
Crea una tabla alfabética:
| Término | Definición | Uso dentro de los videos | Normalización recomendada |

## 10. Terminología que debe normalizarse
Lista errores probables de transcripción, términos dudosos y términos que deben fijarse para el manual.

## 11. Información pendiente de análisis visual
Lista todo lo que no puede confirmarse solo con audio/transcripción y que requiere:
- capturas del video;
- análisis de pantalla;
- OCR;
- revisión manual;
- análisis con modelo visual.

## 12. Material reutilizable para el futuro manual de usuario
Organiza contenido reutilizable en:
- capítulos posibles;
- secciones de manual;
- procedimientos;
- advertencias;
- notas técnicas;
- glosario;
- checklist.

## 13. Limitaciones de esta primera capa
Explica claramente que este informe se basa principalmente en transcripciones e informes preliminares, por lo que debe complementarse con capturas y análisis visual.

## 14. Recomendaciones para la segunda capa documental
Propón los siguientes pasos:
- normalización terminológica;
- extracción de capturas;
- análisis visual de frames;
- vinculación audio-captura;
- creación de informes exhaustivos por segmento;
- generación del manual de usuario.

Reglas:
- Mantén lenguaje técnico claro.
- No reduzcas excesivamente el contenido.
- Conserva la trazabilidad por video.
- No afirmes que algo aparece visualmente si no fue confirmado.
- Si un punto requiere revisión visual, márcalo explícitamente.
- El resultado debe servir como base para construir un manual completo de Volutracer OPUS.

Informes consolidados de entrada:

{contenido_global}
""".strip()


def construir_informe_maestro(
    input_dir: str | Path,
    output_path: str | Path,
    model: str = "gemma3n:e2b",
    temperature: float = 0.2
) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_path = Path(output_path)

    archivos = recolectar_informes_video(input_dir)

    print(f"[INFO] Informes consolidados detectados: {len(archivos)}")
    for archivo in archivos:
        print(f"[INFO] Incluyendo: {archivo.name}")

    prompt = construir_prompt_maestro(archivos)

    print("[INFO] Generando informe maestro global con Ollama...")

    informe = generar_con_ollama(
        prompt=prompt,
        model=model,
        temperature=temperature
    )

    guardar_texto(output_path, informe)

    manifest_path = output_path.with_suffix(".manifest.json")

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump({
            "input_dir": str(input_dir),
            "output_path": str(output_path),
            "model": model,
            "temperature": temperature,
            "total_videos": len(archivos),
            "videos": [archivo.name for archivo in archivos]
        }, f, ensure_ascii=False, indent=2)

    print(f"[OK] Informe maestro guardado en: {output_path}")
    print(f"[OK] Manifest guardado en: {manifest_path}")

    return {
        "output_path": str(output_path),
        "manifest_path": str(manifest_path),
        "total_videos": len(archivos)
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Construye un informe maestro global a partir de informes consolidados por video."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta donde están los informes consolidados por video."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Ruta del informe maestro global de salida."
    )
    parser.add_argument(
        "--model",
        default="gemma3n:e2b",
        help="Modelo de Ollama. Ejemplo: gemma3n:e2b, llama3.1:8b."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperatura del modelo."
    )

    args = parser.parse_args()

    try:
        construir_informe_maestro(
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