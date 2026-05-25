from __future__ import annotations

import json
from typing import Any
from urllib import request, error


OLLAMA_GENERATE_URL = "http://127.0.0.1:11434/api/generate"


def generar_con_ollama(
    prompt: str,
    model: str = "llama3.1:8b",
    temperature: float = 0.2,
    stream: bool = False
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature
        }
    }

    data = json.dumps(payload).encode("utf-8")

    req = request.Request(
        OLLAMA_GENERATE_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with request.urlopen(req, timeout=1800) as response:
            body = response.read().decode("utf-8")

    except error.URLError as e:
        raise RuntimeError(
            "No se pudo conectar con Ollama. "
            "Verifica que Ollama esté activo en http://127.0.0.1:11434."
        ) from e

    if stream:
        partes: list[str] = []
        for linea in body.splitlines():
            if not linea.strip():
                continue
            item = json.loads(linea)
            partes.append(item.get("response", ""))
        return "".join(partes)

    resultado = json.loads(body)
    return resultado.get("response", "")


def probar_ollama(model: str = "llama3.1:8b") -> str:
    prompt = """
You are a system connectivity test.

Return only this exact Spanish phrase:

Ollama funcionando.
""".strip()

    return generar_con_ollama(
        prompt=prompt,
        model=model,
        temperature=0.0
    )


if __name__ == "__main__":
    print(probar_ollama())