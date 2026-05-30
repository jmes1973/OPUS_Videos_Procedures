@'
# Pipeline de segmentación y transcripción

Este flujo está separado del pipeline visual actual de OPUS Videos Procedures.

## Objetivo

Procesar videos largos para obtener una transcripción cruda y trazable.

## Flujo inicial

1. Extraer audio desde video con FFmpeg.
2. Convertir el audio a WAV mono, 16 kHz.
3. Segmentar el audio en bloques controlados.
4. Transcribir cada segmento con Whisper.
5. Guardar salidas crudas: TXT, SRT, VTT y JSON.

## Fuera de alcance por ahora

- Limpieza editorial con Ollama.
- Conversión final a Markdown.
- Integración con análisis visual de frames.
- Corrección clínica o didáctica del texto.

## Estructura de salida esperada

```text
runs/
  run_YYYYMMDD_HHMMSS/
    audio/
      source.wav

    audio_segments/
      segment_000.wav
      segment_001.wav

    transcripts_raw/
      segment_000.txt
      segment_000.srt
      segment_000.vtt
      segment_000.json

    transcription_manifest.json