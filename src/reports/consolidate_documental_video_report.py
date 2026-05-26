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


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def dividir_en_bloques(items: list[Path], chunk_size: int) -> list[list[Path]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def recolectar_informes_documentales(input_dir: str | Path) -> list[Path]:
    input_dir = Path(input_dir)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de informes documentales: {input_dir}")

    archivos = sorted(input_dir.glob("*_informe_documental.md"))

    if not archivos:
        raise FileNotFoundError(f"No se encontraron informes documentales en: {input_dir}")

    return archivos


def construir_prompt_parcial(video_id: str, bloque_num: int, archivos: list[Path]) -> str:
    bloques = []

    for archivo in archivos:
        segmento_id = archivo.name.replace("_informe_documental.md", "")
        contenido = cargar_texto(archivo)

        bloques.append(
            f"""
==============================
SEGMENTO: {segmento_id}
ARCHIVO: {archivo.name}
==============================

{contenido}
""".strip()
        )

    contenido_bloque = "\n\n\n".join(bloques)

    return f"""
Actúa como editor técnico especializado en manuales de usuario para Volutracer OPUS.

Vas a consolidar un bloque parcial de informes documentales por segmento pertenecientes al video {video_id}.

Este consolidado parcial debe conservar la información útil para un futuro manual de usuario.
No hagas un resumen ejecutivo.
No elimines información técnica relevante.
No inventes información.
No afirmes información visual si no fue confirmada.
Conserva trazabilidad por segmento.
Respeta la terminología normalizada:
- Volutracer OPUS
- archivo .STY
- Voluson
- GE Healthcare
- DICOM
- DICOMDIR
- GPS
- Message GPS
- OK Text
- Finish
- Freeze
- caliper
- quiz / quizzes
- MPR
- STIC

Estructura obligatoria:

# Consolidado documental parcial {bloque_num} — Video {video_id}

## 1. Segmentos incluidos

Crea una tabla:

| Segmento | Archivo | Contenido principal | Observaciones |
|---|---|---|---|

## 2. Desarrollo documental del bloque

Organiza el contenido por temas técnicos.
Conserva detalles útiles para manual.
No reduzcas el contenido a generalidades.

## 3. Procedimientos operativos detectados

Para cada procedimiento usa:

### Procedimiento: [nombre]

**Objetivo:**  
**Requisitos previos:**  
**Pasos consolidados:**  
1. ...
2. ...
3. ...

**Resultado esperado:**  
**Advertencias:**  
**Segmentos relacionados:**  
**Pendiente de confirmación visual:**  

## 4. Campos, parámetros, archivos o configuraciones de Volutracer OPUS

Crea una tabla:

| Elemento | Tipo | Función | Valores o acciones mencionadas | Efecto en el sistema | Precauciones | Segmentos |
|---|---|---|---|---|---|---|

## 5. Atajos, teclas y comandos

Crea una tabla:

| Atajo / comando | Función | Contexto de uso | Resultado esperado | Segmentos |
|---|---|---|---|---|

Si no aparecen atajos, indícalo claramente.

## 6. Conceptos técnicos y definiciones

Crea una tabla:

| Concepto | Definición documental | Contexto de uso | Segmentos relacionados |
|---|---|---|---|

## 7. Advertencias técnicas y riesgos

Crea una tabla:

| Advertencia | Riesgo | Impacto | Prevención sugerida | Segmentos |
|---|---|---|---|---|

## 8. Glosario parcial

Crea una tabla:

| Término | Definición normalizada | Uso dentro del bloque |
|---|---|---|

## 9. Dudas y pendientes

Separa:
- dudas terminológicas;
- dudas funcionales;
- dudas visuales;
- dudas pedagógicas o de manualización.

## 10. Material reutilizable para manual

Incluye:
- texto posible para manual;
- procedimientos reutilizables;
- tablas reutilizables;
- advertencias reutilizables;
- glosario reutilizable.

Informes documentales del bloque:

{contenido_bloque}
""".strip()


def construir_prompt_final(video_id: str, parciales: list[Path]) -> str:
    bloques = []

    for parcial in parciales:
        contenido = cargar_texto(parcial)
        bloques.append(
            f"""
==============================
CONSOLIDADO PARCIAL: {parcial.name}
==============================

{contenido}
""".strip()
        )

    contenido_parciales = "\n\n\n".join(bloques)

    return f"""
Actúa como editor técnico maestro especializado en documentación de software médico, simulación ecográfica y manuales de usuario.

Vas a construir el informe documental consolidado del video {video_id}, a partir de consolidados parciales generados desde informes documentales por segmento.

Este informe debe servir como base directa para un futuro manual de usuario de Volutracer OPUS.

No hagas un resumen ejecutivo.
No elimines información técnica relevante.
No inventes información.
No afirmes información visual si no fue confirmada.
Conserva trazabilidad por segmento o bloque parcial cuando sea posible.
Une redundancias sin perder matices importantes.
Respeta terminología normalizada:
- Volutracer OPUS
- archivo .STY
- Voluson
- GE Healthcare
- DICOM
- DICOMDIR
- GPS
- Message GPS
- OK Text
- Finish
- Freeze
- caliper
- quiz / quizzes
- MPR
- STIC

Estructura obligatoria:

# Informe documental consolidado — Video {video_id}

## 1. Identificación general

Incluye:
- Video:
- Fuente:
- Tipo de informe:
- Alcance:
- Limitación principal:

## 2. Estructura de bloques y segmentos

Crea una tabla:

| Bloque parcial | Segmentos incluidos | Contenido principal | Observaciones |
|---|---|---|---|

## 3. Desarrollo técnico-documental del video

Organiza el contenido por temas mayores.
Debe leerse como base de manual, no como comentario breve.

## 4. Procedimientos consolidados del video

Para cada procedimiento usa:

### Procedimiento: [nombre]

**Objetivo:**  
**Requisitos previos:**  
**Pasos consolidados:**  
1. ...
2. ...
3. ...

**Resultado esperado:**  
**Advertencias:**  
**Bloques o segmentos relacionados:**  
**Pendiente de confirmación visual:**  

## 5. Campos, parámetros, archivos y configuraciones de Volutracer OPUS

Crea una tabla:

| Elemento | Tipo | Función | Valores o acciones mencionadas | Efecto en el sistema | Precauciones | Segmentos / bloques |
|---|---|---|---|---|---|---|

## 6. Atajos, teclas y comandos

Crea una tabla:

| Atajo / comando | Función | Contexto de uso | Resultado esperado | Confirmación pendiente |
|---|---|---|---|---|

## 7. Conceptos técnicos consolidados

Crea una tabla:

| Concepto | Definición documental | Contexto de uso en el video | Relación con otros conceptos |
|---|---|---|---|

## 8. Advertencias técnicas y riesgos

Crea una tabla:

| Advertencia | Riesgo | Impacto | Prevención sugerida | Confirmación pendiente |
|---|---|---|---|---|

## 9. Glosario técnico del video

Crea una tabla alfabética:

| Término | Definición normalizada | Uso dentro del video | Observaciones |
|---|---|---|---|

## 10. Dudas y pendientes

Separa:
### 10.1 Dudas terminológicas
### 10.2 Dudas funcionales
### 10.3 Dudas visuales
### 10.4 Dudas pedagógicas o de manualización

## 11. Material reutilizable para manual

Organiza:
### 11.1 Texto posible para manual
### 11.2 Procedimientos reutilizables
### 11.3 Tablas reutilizables
### 11.4 Advertencias reutilizables
### 11.5 Glosario reutilizable

## 12. Evaluación de completitud del video

Indica:
- qué quedó suficientemente documentado;
- qué falta;
- qué necesita capturas;
- qué puede pasar a manual preliminar.

Consolidados parciales:

{contenido_parciales}
""".strip()


def consolidar_documental_video(
    video_id: str,
    input_dir: str | Path,
    output_dir: str | Path,
    chunk_size: int = 1,
    model: str = "gemma3n:e2b",
    temperature: float = 0.2
) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    informes = recolectar_informes_documentales(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parciales_dir = output_dir / f"{video_id}_documental_parciales"
    parciales_dir.mkdir(parents=True, exist_ok=True)

    bloques = dividir_en_bloques(informes, chunk_size)
    parciales_generados: list[Path] = []

    print(f"[INFO] Video: {video_id}")
    print(f"[INFO] Informes documentales detectados: {len(informes)}")
    print(f"[INFO] Bloques parciales: {len(bloques)}")
    print(f"[INFO] Chunk size: {chunk_size}")

    for i, bloque in enumerate(bloques, start=1):
        parcial_path = parciales_dir / f"{video_id}_documental_parcial_{i:02d}.md"

        if parcial_path.exists():
            print(f"[SKIP] Ya existe parcial documental: {parcial_path.name}")
            parciales_generados.append(parcial_path)
            continue

        print(f"[INFO] Consolidando parcial documental {i}/{len(bloques)} con {len(bloque)} segmento(s)...")

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

        print(f"[OK] Parcial documental guardado: {parcial_path}")

    final_path = output_dir / f"{video_id}_informe_documental_consolidado.md"

    print(f"[INFO] Generando informe documental final desde {len(parciales_generados)} parciales...")

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

    manifest_path = output_dir / f"{video_id}_informe_documental_consolidado.manifest.json"

    guardar_json(
        manifest_path,
        {
            "video_id": video_id,
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "chunk_size": chunk_size,
            "model": model,
            "temperature": temperature,
            "total_segment_reports": len(informes),
            "total_partial_reports": len(parciales_generados),
            "partials": [str(p) for p in parciales_generados],
            "final_report": str(final_path)
        }
    )

    print(f"[OK] Informe documental consolidado guardado en: {final_path}")
    print(f"[OK] Manifest guardado en: {manifest_path}")

    return {
        "video_id": video_id,
        "final_report": str(final_path),
        "manifest": str(manifest_path),
        "total_partials": len(parciales_generados)
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolida informes documentales por segmento en un informe documental por video."
    )

    parser.add_argument("--video-id", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--chunk-size", type=int, default=1)
    parser.add_argument("--model", default="gemma3n:e2b")
    parser.add_argument("--temperature", type=float, default=0.2)

    args = parser.parse_args()

    try:
        consolidar_documental_video(
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