from __future__ import annotations

from pathlib import Path
import argparse
import json
import re
from typing import Any


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta: str | Path, contenido: dict[str, Any]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)


def cargar_texto(ruta: str | Path) -> str:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8") as f:
        return f.read()


def guardar_texto(ruta: str | Path, contenido: str) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        f.write(contenido)


def compilar_regla(variante: str) -> re.Pattern:
    """
    Compila una regla de reemplazo segura.

    Usa límites de palabra cuando la variante es alfanumérica.
    Para variantes con signos como .STI, aplica escape directo.
    """
    variante_escapada = re.escape(variante)

    if re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9 ]+", variante):
        patron = rf"\b{variante_escapada}\b"
    else:
        patron = variante_escapada

    return re.compile(patron, flags=re.IGNORECASE)


def preservar_mayusculas_basicas(original: str, canonical: str) -> str:
    """
    Mantiene el término canónico tal como está definido.
    No intenta copiar mayúsculas del original porque en este proyecto
    queremos normalización estricta: DICOM, STIC, MPR, archivo .STY, etc.
    """
    return canonical


def aplicar_terminologia(
    texto: str,
    terms_config: dict[str, Any]
) -> tuple[str, list[dict[str, Any]]]:
    cambios: list[dict[str, Any]] = []
    texto_normalizado = texto

    terms = terms_config.get("terms", [])

    # Ordenar variantes de más largas a más cortas para evitar reemplazos parciales.
    reglas: list[dict[str, Any]] = []

    for term in terms:
        canonical = term.get("canonical", "").strip()
        variants = term.get("replace_variants", [])
        category = term.get("category", "")
        confidence = term.get("confidence", "")
        preferred_usage = term.get("preferred_usage", "")

        if not canonical:
            continue

        for variant in variants:
            variant = str(variant).strip()
            if not variant:
                continue

            # Evita reemplazar si variante y canónico son exactamente iguales.
            # Aun así se permite si cambia capitalización, por ejemplo dicom → DICOM.
            reglas.append({
                "variant": variant,
                "canonical": canonical,
                "category": category,
                "confidence": confidence,
                "preferred_usage": preferred_usage,
                "pattern": compilar_regla(variant)
            })

    reglas.sort(key=lambda r: len(r["variant"]), reverse=True)

    for regla in reglas:
        variant = regla["variant"]
        canonical = regla["canonical"]
        pattern = regla["pattern"]

        matches = list(pattern.finditer(texto_normalizado))
        if not matches:
            continue

        count = len(matches)

        def reemplazar(match: re.Match) -> str:
            original = match.group(0)
            return preservar_mayusculas_basicas(original, canonical)

        texto_normalizado = pattern.sub(reemplazar, texto_normalizado)

        cambios.append({
            "from": variant,
            "to": canonical,
            "count": count,
            "category": regla["category"],
            "confidence": regla["confidence"],
            "preferred_usage": regla["preferred_usage"]
        })

    return texto_normalizado, cambios


def normalizar_archivo(
    input_path: str | Path,
    output_path: str | Path,
    terms_config: dict[str, Any]
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)

    texto_original = cargar_texto(input_path)
    texto_normalizado, cambios = aplicar_terminologia(
        texto=texto_original,
        terms_config=terms_config
    )

    guardar_texto(output_path, texto_normalizado)

    return {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "changes": cambios,
        "total_change_groups": len(cambios),
        "total_replacements": sum(c["count"] for c in cambios)
    }


def recolectar_txt(input_dir: str | Path) -> list[Path]:
    input_dir = Path(input_dir)
    return sorted(input_dir.rglob("*.txt"))


def construir_salida_equivalente(
    input_file: Path,
    input_root: Path,
    output_root: Path
) -> Path:
    relative_path = input_file.relative_to(input_root)
    return output_root / relative_path


def normalizar_carpeta(
    input_dir: str | Path,
    output_dir: str | Path,
    terms_path: str | Path
) -> Path:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    terms_path = Path(terms_path)

    if not input_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta de entrada: {input_dir}")

    if not terms_path.exists():
        raise FileNotFoundError(f"No existe el diccionario terminológico: {terms_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    terms_config = cargar_json(terms_path)
    archivos = recolectar_txt(input_dir)

    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos .txt en: {input_dir}")

    resultados: list[dict[str, Any]] = []

    for archivo in archivos:
        output_path = construir_salida_equivalente(
            input_file=archivo,
            input_root=input_dir,
            output_root=output_dir
        )

        print(f"[INFO] Normalizando: {archivo.relative_to(input_dir)}")

        resultado = normalizar_archivo(
            input_path=archivo,
            output_path=output_path,
            terms_config=terms_config
        )
        resultados.append(resultado)

    manifest_path = output_dir / "normalization_manifest.json"

    resumen_por_termino: dict[str, int] = {}

    for resultado in resultados:
        for cambio in resultado["changes"]:
            clave = f"{cambio['from']} -> {cambio['to']}"
            resumen_por_termino[clave] = resumen_por_termino.get(clave, 0) + cambio["count"]

    guardar_json(
        manifest_path,
        {
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "terms_path": str(terms_path),
            "total_files": len(archivos),
            "total_change_groups": sum(r["total_change_groups"] for r in resultados),
            "total_replacements": sum(r["total_replacements"] for r in resultados),
            "summary_by_replacement": resumen_por_termino,
            "files": resultados
        }
    )

    print(f"[OK] Manifest de normalización guardado en: {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normaliza terminología técnica en transcripciones TXT."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta raíz donde están las transcripciones originales."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta donde se guardarán las transcripciones normalizadas."
    )
    parser.add_argument(
        "--terms",
        default="config/manual_terms.json",
        help="Ruta al diccionario terminológico JSON."
    )

    args = parser.parse_args()

    try:
        normalizar_carpeta(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            terms_path=args.terms
        )
        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())