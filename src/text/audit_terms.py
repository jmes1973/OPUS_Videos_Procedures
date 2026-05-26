from __future__ import annotations

from pathlib import Path
import argparse
import csv
import re
from collections import Counter, defaultdict
from typing import Any


STOPWORDS = {
    "que", "para", "con", "una", "uno", "los", "las", "del", "por", "como",
    "este", "esta", "esto", "son", "hay", "más", "pero", "también", "entonces",
    "vamos", "puede", "pueden", "debe", "deben", "hacer", "tener", "desde",
    "donde", "cuando", "porque", "sobre", "entre", "cada", "bien", "aquí",
    "allí", "ahora", "luego", "solo", "todo", "toda", "todos", "todas",
    "the", "and", "for", "with", "this", "that", "from", "into", "then"
}


CORRECCIONES_CONOCIDAS = {
    "volusion": "Voluson",
    "voluson": "Voluson",
    "volusson": "Voluson",
    "voluzon": "Voluson",
    "boluson": "Voluson",

    "dicom": "DICOM",
    "dicon": "DICOM",
    "dicomdir": "DICOMDIR",

    "opus": "OPUS",
    "volutracer opus": "Volutracer OPUS",

    "sti": "archivo .STI",
    ".sti": "archivo .STI",

    "stic": "STIC",
    "mpr": "MPR",
    "gps": "GPS",

    "freeze": "Freeze",
    "finish": "Finish",
    "ok text": "OK Text",
    "message gps": "Message GPS",

    "caliper": "caliper",
    "calipers": "calipers",

    "quiz": "quiz",
    "quices": "quizzes",
    "quizzes": "quizzes",

    "cabum": "cavum",
    "cavum": "cavum",

    "ge": "GE Healthcare",
    "ge healthcare": "GE Healthcare",
}


TERMINOS_CRITICOS = [
    "Voluson",
    "DICOM",
    "DICOMDIR",
    "Volutracer OPUS",
    "OPUS",
    "archivo .STI",
    "STIC",
    "MPR",
    "GPS",
    "Message GPS",
    "OK Text",
    "Finish",
    "Freeze",
    "caliper",
    "calipers",
    "quiz",
    "quizzes",
    "cavum",
    "GE Healthcare",
]


def limpiar_linea(linea: str) -> str:
    linea = re.sub(r"\[\d+(\.\d+)?\s*-\s*\d+(\.\d+)?\]", "", linea)
    linea = linea.replace(":", " ")
    return linea.strip()


def tokenizar(texto: str) -> list[str]:
    texto = texto.lower()
    tokens = re.findall(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ0-9\.\-]+", texto)
    return [t.strip(".-,;:()[]{}") for t in tokens if len(t.strip(".-,;:()[]{}")) >= 2]


def extraer_ngramas(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def recolectar_transcripciones(input_dir: Path) -> list[Path]:
    return sorted(input_dir.rglob("*.txt"))


def obtener_contextos(
    archivos: list[Path],
    terminos: list[str],
    max_contextos: int = 5
) -> dict[str, list[str]]:
    contextos: dict[str, list[str]] = defaultdict(list)

    terminos_lower = [t.lower() for t in terminos]

    for archivo in archivos:
        with archivo.open("r", encoding="utf-8") as f:
            for linea in f:
                linea_limpia = limpiar_linea(linea)
                linea_lower = linea_limpia.lower()

                for termino in terminos_lower:
                    if termino in linea_lower and len(contextos[termino]) < max_contextos:
                        contextos[termino].append(f"{archivo.parent.name}/{archivo.name}: {linea_limpia}")

    return contextos


def auditar_terminos(input_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    archivos = recolectar_transcripciones(input_dir)

    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos .txt en: {input_dir}")

    contador_tokens: Counter[str] = Counter()
    contador_bigramas: Counter[str] = Counter()
    contador_trigramas: Counter[str] = Counter()

    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8")
        lineas = [limpiar_linea(l) for l in texto.splitlines()]
        texto_limpio = " ".join(lineas)
        tokens = tokenizar(texto_limpio)

        tokens_filtrados = [
            t for t in tokens
            if t not in STOPWORDS and not t.isdigit() and len(t) >= 3
        ]

        contador_tokens.update(tokens_filtrados)
        contador_bigramas.update(extraer_ngramas(tokens_filtrados, 2))
        contador_trigramas.update(extraer_ngramas(tokens_filtrados, 3))

    candidatos: list[dict[str, Any]] = []

    for termino, frecuencia in contador_tokens.most_common():
        sugerido = CORRECCIONES_CONOCIDAS.get(termino, "")
        if frecuencia >= 2 or sugerido:
            candidatos.append({
                "termino_detectado": termino,
                "frecuencia": frecuencia,
                "tipo": "token",
                "sugerido": sugerido,
                "accion": "corregir" if sugerido and sugerido.lower() != termino.lower() else "revisar"
            })

    for termino, frecuencia in contador_bigramas.most_common(300):
        sugerido = CORRECCIONES_CONOCIDAS.get(termino, "")
        if sugerido or any(t.lower() in termino for t in TERMINOS_CRITICOS):
            candidatos.append({
                "termino_detectado": termino,
                "frecuencia": frecuencia,
                "tipo": "bigrama",
                "sugerido": sugerido,
                "accion": "corregir" if sugerido else "revisar"
            })

    for termino, frecuencia in contador_trigramas.most_common(300):
        sugerido = CORRECCIONES_CONOCIDAS.get(termino, "")
        if sugerido or "volutracer" in termino or "ge healthcare" in termino:
            candidatos.append({
                "termino_detectado": termino,
                "frecuencia": frecuencia,
                "tipo": "trigrama",
                "sugerido": sugerido,
                "accion": "corregir" if sugerido else "revisar"
            })

    # Quitar duplicados preservando orden
    vistos = set()
    candidatos_unicos = []
    for item in candidatos:
        clave = (item["termino_detectado"], item["tipo"])
        if clave not in vistos:
            vistos.add(clave)
            candidatos_unicos.append(item)

    terminos_para_contexto = [c["termino_detectado"] for c in candidatos_unicos[:200]]
    contextos = obtener_contextos(archivos, terminos_para_contexto)

    csv_path = output_dir / "terminos_auditoria.csv"
    md_path = output_dir / "terminos_auditoria.md"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "termino_detectado",
                "frecuencia",
                "tipo",
                "sugerido",
                "accion",
                "contextos"
            ]
        )
        writer.writeheader()

        for item in candidatos_unicos:
            termino = item["termino_detectado"]
            item_contextos = contextos.get(termino.lower(), [])
            writer.writerow({
                **item,
                "contextos": " || ".join(item_contextos)
            })

    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Auditoría terminológica global\n\n")
        f.write(f"Archivos analizados: {len(archivos)}\n\n")
        f.write("## Términos críticos esperados\n\n")
        for termino in TERMINOS_CRITICOS:
            f.write(f"- {termino}\n")

        f.write("\n## Candidatos detectados\n\n")
        f.write("| Término detectado | Frecuencia | Tipo | Sugerido | Acción |\n")
        f.write("|---|---:|---|---|---|\n")

        for item in candidatos_unicos[:300]:
            f.write(
                f"| {item['termino_detectado']} | {item['frecuencia']} | "
                f"{item['tipo']} | {item['sugerido']} | {item['accion']} |\n"
            )

        f.write("\n## Contextos de revisión\n\n")
        for item in candidatos_unicos[:100]:
            termino = item["termino_detectado"]
            item_contextos = contextos.get(termino.lower(), [])
            if not item_contextos:
                continue

            f.write(f"\n### {termino}\n\n")
            for contexto in item_contextos:
                f.write(f"- {contexto}\n")

    return {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "archivos_analizados": len(archivos),
        "csv": str(csv_path),
        "markdown": str(md_path),
        "total_candidatos": len(candidatos_unicos)
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audita términos técnicos en transcripciones TXT."
    )

    parser.add_argument(
        "--input-dir",
        required=True,
        help="Carpeta raíz donde están las transcripciones."
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Carpeta de salida para auditoría terminológica."
    )

    args = parser.parse_args()

    try:
        resultado = auditar_terminos(
            input_dir=args.input_dir,
            output_dir=args.output_dir
        )

        print("[OK] Auditoría terminológica generada.")
        print(f"[OK] Archivos analizados: {resultado['archivos_analizados']}")
        print(f"[OK] CSV: {resultado['csv']}")
        print(f"[OK] Markdown: {resultado['markdown']}")
        print(f"[OK] Candidatos: {resultado['total_candidatos']}")

        return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())