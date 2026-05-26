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


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def construir_bloque_terminologia(terms_config: dict[str, Any]) -> str:
    terms = terms_config.get("terms", [])

    lineas = [
        "Terminología obligatoria del proyecto:",
        "",
        "Usa estos términos canónicos. No uses variantes fonéticas ni formas no normalizadas.",
        ""
    ]

    for term in terms:
        canonical = term.get("canonical", "")
        category = term.get("category", "")
        definition = term.get("definition", "")
        preferred_usage = term.get("preferred_usage", "")

        if not canonical:
            continue

        lineas.append(f"- {canonical}")
        if category:
            lineas.append(f"  Categoría: {category}")
        if definition:
            lineas.append(f"  Definición: {definition}")
        if preferred_usage:
            lineas.append(f"  Uso recomendado: {preferred_usage}")
        lineas.append("")

    return "\n".join(lineas).strip()


def construir_prompt_documental(
    segmento_id: str,
    transcripcion_normalizada: str,
    terms_config: dict[str, Any]
) -> str:
    bloque_terminologia = construir_bloque_terminologia(terms_config)

    return f"""
Actúa como redactor técnico, analista documental y arquitecto de manuales de usuario para software de simulación ecográfica.

Vas a analizar una transcripción normalizada de un segmento de video sobre Volutracer OPUS.

Objetivo:
Construir un informe documental exhaustivo por segmento, orientado a servir como materia prima para un futuro manual de usuario de Volutracer OPUS.

Este informe NO es un resumen.
Este informe debe conservar la mayor cantidad posible de información útil de la transcripción.
Este informe debe ordenar, aclarar y estructurar la información, sin inventar datos que no estén en la transcripción.

Segmento:
{segmento_id}

{bloque_terminologia}

Reglas obligatorias:

1. No inventes información.
2. No afirmes que algo se ve en pantalla, porque en esta capa todavía no se analizan capturas.
3. Diferencia claramente:
   - información dicha en el audio;
   - inferencia técnica razonable;
   - información pendiente de confirmación visual.
4. Usa la terminología canónica indicada.
5. Si detectas una palabra rara o dudosa, no la conviertas en certeza; márcala como duda terminológica.
6. Mantén el detalle. No reduzcas el segmento a ideas generales.
7. Extrae procedimientos en pasos operativos cuando sea posible.
8. Extrae parámetros, campos, comandos, atajos, archivos y configuraciones mencionadas.
9. Organiza el contenido para que pueda convertirse después en manual.
10. Si un punto depende del video o la interfaz, márcalo como pendiente de revisión visual.

Estructura obligatoria de salida:

# Informe documental del segmento {segmento_id}

## 1. Identificación del segmento

Incluye:
- Segmento:
- Fuente analizada:
- Tipo de fuente:
- Alcance:
- Limitación principal de esta capa:

## 2. Transcripción normalizada interpretada

Reescribe el contenido del segmento en forma documental, conservando los detalles relevantes.
No lo conviertas en resumen.
Respeta el orden lógico de la explicación original.
Si hay términos dudosos, márcalos.

## 3. Temas tratados en el segmento

Crea una tabla:

| Tema | Desarrollo | Evidencia en la transcripción | Pendiente de confirmación visual |
|---|---|---|---|

## 4. Conceptos técnicos identificados

Crea una tabla:

| Concepto | Definición documental | Contexto dentro del segmento | Relación con otros conceptos | Nivel de certeza |
|---|---|---|---|---|

## 5. Procedimientos operativos detectados

Por cada procedimiento usa esta estructura:

### Procedimiento: [nombre del procedimiento]

**Objetivo:**  
**Requisitos previos:**  
**Pasos documentados:**  
1. ...
2. ...
3. ...

**Resultado esperado:**  
**Advertencias:**  
**Pendiente de confirmación visual:**  

Si no hay suficiente información para completar un procedimiento, conserva lo disponible y marca lo faltante.

## 6. Campos, parámetros, archivos o configuraciones de Volutracer OPUS

Crea una tabla:

| Elemento | Tipo | Función | Valores o acciones mencionadas | Efecto en el sistema | Precauciones |
|---|---|---|---|---|---|

Incluye, si aparecen:
- archivo .STY
- Message GPS
- OK Text
- Finish
- Sound
- Freeze
- zoom
- quiz
- caliper
- DICOM
- Voluson
- MPR
- STIC
- cualquier otro parámetro o campo mencionado.

## 7. Atajos, teclas y comandos

Crea una tabla:

| Atajo / comando | Función | Contexto de uso | Resultado esperado | Confirmación |
|---|---|---|---|---|

Si no se identifican atajos, indícalo claramente.

## 8. Advertencias técnicas y riesgos

Crea una tabla:

| Advertencia | Riesgo | Impacto | Prevención sugerida | Pendiente de confirmar |
|---|---|---|---|---|

## 9. Glosario del segmento

Crea una tabla:

| Término | Definición normalizada | Uso en el segmento | Observación |
|---|---|---|---|

## 10. Dudas y puntos pendientes

Separa en:

### 10.1 Dudas terminológicas
### 10.2 Dudas funcionales
### 10.3 Dudas visuales
### 10.4 Dudas pedagógicas o de manualización

## 11. Material reutilizable para manual

Organiza el contenido reutilizable en:

### 11.1 Texto posible para manual
### 11.2 Procedimientos reutilizables
### 11.3 Tablas reutilizables
### 11.4 Advertencias reutilizables
### 11.5 Glosario reutilizable

## 12. Evaluación de completitud del segmento

Indica:
- Qué información parece suficientemente documentada.
- Qué información falta.
- Qué debería revisarse posteriormente con capturas.
- Qué podría pasar directamente a un manual preliminar.

Transcripción normalizada:

{transcripcion_normalizada}
""".strip()


def analizar_transcripcion_documental(
    transcript_path: str | Path,
    output_dir: str | Path,
    terms_config: dict[str, Any],
    model: str = "gemma3n:e2b",
    temperature: float = 0.2
) -> dict[str, Any]:
    transcript_path = Path(transcript_path)
    output_dir = Path(output_dir)

    if not transcript_path.exists():
        raise FileNotFoundError(f"No existe la transcripción: {transcript_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    segmento_id = transcript_path.stem
    output_path = output_dir / f"{segmento_id}_informe_documental.md"

    if output_path.exists():
        print(f"[SKIP] Ya existe informe documental: {output_path.name}")
        return {
            "segmento_id": segmento_id,
            "transcript_path": str(transcript_path),
            "output_path": str(output_path),
            "model": model,
            "status": "skipped_existing"
        }

    transcripcion_normalizada = cargar_texto(transcript_path)

    prompt = construir_prompt_documental(
        segmento_id=segmento_id,
        transcripcion_normalizada=transcripcion_normalizada,
        terms_config=terms_config
    )

    print(f"[INFO] Generando informe documental: {segmento_id}")

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


def analizar_carpeta_documental(
    input_dir: str | Path,
    output_dir: str | Path,
    terms_path: str | Path,
    model: str = "gemma3n:e2b",
    temperature: float = 0.2
) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    terms_path = Path(terms_path)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de transcripciones normalizadas: {input_dir}")

    if not terms_path.exists():
        raise FileNotFoundError(f"No existe el diccionario terminológico: {terms_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    terms_config = cargar_json(terms_path)
    transcripciones = sorted(input_dir.rglob("*.txt"))

    if not transcripciones:
        raise FileNotFoundError(f"No se encontraron archivos .txt en: {input_dir}")

    resultados: list[dict[str, Any]] = []

    for transcript_path in transcripciones:
        # Mantiene subcarpetas V01, V02, etc. en la salida.
        relative_parent = transcript_path.parent.relative_to(input_dir)
        output_subdir = output_dir / relative_parent

        resultado = analizar_transcripcion_documental(
            transcript_path=transcript_path,
            output_dir=output_subdir,
            terms_config=terms_config,
            model=model,
            temperature=temperature
        )
        resultados.append(resultado)

    manifest_path = output_dir / "documental_analysis_manifest.json"

    guardar_json(
        manifest_path,
        {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "terms_path": str(terms_path),
            "model": model,
            "temperature": temperature,
            "total_transcripciones": len(transcripciones),
            "created": sum(1 for r in resultados if r["status"] == "created"),
            "skipped_existing": sum(1 for r in resultados if r["status"] == "skipped_existing"),
            "analisis": resultados
        }
    )

    print(f"[OK] Manifest de análisis documental guardado en: {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera informes documentales por segmento desde transcripciones normalizadas."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta raíz de transcripciones normalizadas."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta raíz donde se guardarán los informes documentales por segmento."
    )
    parser.add_argument(
        "--terms",
        default="config/manual_terms.json",
        help="Ruta del diccionario terminológico."
    )
    parser.add_argument(
        "--model",
        default="gemma3n:e2b",
        help="Modelo de Ollama."
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperatura de generación."
    )

    args = parser.parse_args()

    try:
        analizar_carpeta_documental(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            terms_path=args.terms,
            model=args.model,
            temperature=args.temperature
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())