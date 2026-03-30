from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def cargar_json(ruta: str | Path) -> dict[str, Any]:
    ruta = Path(ruta)
    with ruta.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def debe_escalar_a_capa_2(
    clasificacion_preliminar: dict[str, Any],
    reglas: dict[str, Any]
) -> bool:
    umbrales = reglas.get("umbrales", {})
    criterios = reglas.get("criterios_escalamiento", {})

    confianza = float(clasificacion_preliminar.get("confianza", 0.0))
    especificidad = clasificacion_preliminar.get("especificidad", "baja")
    ocr_calidad = float(clasificacion_preliminar.get("ocr_calidad", 0.0))
    tiene_conflicto = bool(clasificacion_preliminar.get("conflicto_reglas", False))
    impacto_alto = bool(clasificacion_preliminar.get("impacto_alto_en_guia", True))

    if confianza < float(umbrales.get("confianza_minima_sin_escalar", 0.8)):
        return True

    if especificidad == "baja" and criterios.get("evento_demasiado_generico", True):
        return True

    if ocr_calidad < float(umbrales.get("ocr_calidad_minima", 0.65)) and criterios.get("ocr_insuficiente", True):
        return True

    if tiene_conflicto and criterios.get("conflicto_entre_reglas", True):
        return True

    if impacto_alto and criterios.get("impacto_alto_en_guia_final", True) and confianza < 0.9:
        return True

    return False
