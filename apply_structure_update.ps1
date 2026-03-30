# ==========================================
# apply_structure_update.ps1
# Ajuste de estructura para opus-video-procedures
# Ejecutar desde la raíz del repositorio
# ==========================================

$ErrorActionPreference = "Stop"

Write-Host "Aplicando actualización de estructura..." -ForegroundColor Cyan

# Verificar que estamos en la raíz esperada
if (-not (Test-Path ".\src")) {
    Write-Host "Error: no se encontró la carpeta .\src. Ejecuta este script desde la raíz del proyecto." -ForegroundColor Red
    exit 1
}

# -------------------------------------------------
# 1. Crear nuevas carpetas principales
# -------------------------------------------------
$dirs = @(
    ".\runs",
    ".\runs\_template_run",
    ".\runs\_template_run\frames",
    ".\runs\_template_run\frames_index",
    ".\runs\_template_run\events_raw",
    ".\runs\_template_run\timeline_raw",
    ".\runs\_template_run\steps_normalized",
    ".\runs\_template_run\capture_plan",
    ".\runs\_template_run\reports",
    ".\runs\_template_run\guides",
    ".\runs\_template_run\logs",

    ".\schemas",

    ".\templates\json",

    ".\src\core",
    ".\src\extraction",
    ".\src\analysis",
    ".\src\qa"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Creada carpeta: $dir" -ForegroundColor Green
    }
    else {
        Write-Host "Ya existe: $dir" -ForegroundColor DarkYellow
    }
}

# -------------------------------------------------
# 2. Crear nuevos archivos JSON de configuración
# -------------------------------------------------
$actionLexiconPath = ".\config\action_lexicon.json"
if (-not (Test-Path $actionLexiconPath)) {
@'
{
  "acciones_permitidas": [
    "inicio",
    "abrir_panel",
    "cerrar_panel",
    "seleccionar_opcion",
    "cambiar_selector",
    "activar_control",
    "desactivar_control",
    "desplazar_slider",
    "confirmar_cambio",
    "error_visible"
  ]
}
'@ | Set-Content -Path $actionLexiconPath -Encoding UTF8
    Write-Host "Creado: $actionLexiconPath" -ForegroundColor Green
}
else {
    Write-Host "Ya existe: $actionLexiconPath" -ForegroundColor DarkYellow
}

# -------------------------------------------------
# 3. Crear schemas JSON base
# -------------------------------------------------
$schemaFiles = @{
    ".\schemas\frames_index.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "frames_index",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "generated_at": { "type": "string" },
    "frames": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "frame_id": { "type": "string" },
          "timestamp": { "type": "string" },
          "path": { "type": "string" },
          "hash": { "type": "string" },
          "is_keyframe": { "type": "boolean" },
          "change_score": { "type": "number" }
        },
        "required": ["frame_id", "timestamp", "path"]
      }
    }
  },
  "required": ["video_id", "frames"]
}
'@;

    ".\schemas\events_raw.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "events_raw",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "events": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "event_id": { "type": "string" },
          "start_time": { "type": "string" },
          "end_time": { "type": "string" },
          "event_type": { "type": "string" },
          "observable_action": { "type": "string" },
          "evidence_frames": {
            "type": "array",
            "items": { "type": "string" }
          },
          "certainty": { "type": "string" },
          "notes": { "type": "string" }
        },
        "required": ["event_id", "start_time", "event_type", "observable_action"]
      }
    }
  },
  "required": ["video_id", "events"]
}
'@;

    ".\schemas\timeline_raw.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "timeline_raw",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "timeline": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sequence_id": { "type": "string" },
          "event_ids": {
            "type": "array",
            "items": { "type": "string" }
          },
          "summary": { "type": "string" },
          "start_time": { "type": "string" },
          "end_time": { "type": "string" }
        },
        "required": ["sequence_id", "event_ids", "summary"]
      }
    }
  },
  "required": ["video_id", "timeline"]
}
'@;

    ".\schemas\steps_normalized.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "steps_normalized",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step_id": { "type": "string" },
          "title": { "type": "string" },
          "description": { "type": "string" },
          "source_events": {
            "type": "array",
            "items": { "type": "string" }
          },
          "certainty": { "type": "string" },
          "requires_manual_review": { "type": "boolean" }
        },
        "required": ["step_id", "title", "source_events"]
      }
    }
  },
  "required": ["video_id", "steps"]
}
'@;

    ".\schemas\capture_plan.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "capture_plan",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "captures": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "capture_id": { "type": "string" },
          "step_id": { "type": "string" },
          "frame_id": { "type": "string" },
          "reason": { "type": "string" }
        },
        "required": ["capture_id", "step_id", "frame_id"]
      }
    }
  },
  "required": ["video_id", "captures"]
}
'@;

    ".\schemas\qa_report.schema.json" = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "qa_report",
  "type": "object",
  "properties": {
    "video_id": { "type": "string" },
    "status": { "type": "string" },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "issue_id": { "type": "string" },
          "severity": { "type": "string" },
          "message": { "type": "string" },
          "related_ids": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "required": ["issue_id", "severity", "message"]
      }
    }
  },
  "required": ["video_id", "status", "issues"]
}
'@
}

foreach ($file in $schemaFiles.Keys) {
    if (-not (Test-Path $file)) {
        $schemaFiles[$file] | Set-Content -Path $file -Encoding UTF8
        Write-Host "Creado: $file" -ForegroundColor Green
    }
    else {
        Write-Host "Ya existe: $file" -ForegroundColor DarkYellow
    }
}

# -------------------------------------------------
# 4. Crear plantillas JSON nuevas
# -------------------------------------------------
$templateFiles = @{
    ".\templates\json\timeline_raw_template.json" = @'
{
  "video_id": "",
  "timeline": []
}
'@;

    ".\templates\json\capture_plan_template.json" = @'
{
  "video_id": "",
  "captures": []
}
'@
}

foreach ($file in $templateFiles.Keys) {
    if (-not (Test-Path $file)) {
        $templateFiles[$file] | Set-Content -Path $file -Encoding UTF8
        Write-Host "Creado: $file" -ForegroundColor Green
    }
    else {
        Write-Host "Ya existe: $file" -ForegroundColor DarkYellow
    }
}

# -------------------------------------------------
# 5. Crear módulos Python nuevos recomendados
# -------------------------------------------------
$pythonFiles = @{
    ".\src\core\paths.py" = @'
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "runs"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
'@;

    ".\src\core\run_manager.py" = @'
from pathlib import Path
from datetime import datetime

def create_run_dir(base_dir: Path) -> Path:
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
'@;

    ".\src\extraction\frames_indexer.py" = @'
def build_frames_index(frames_metadata):
    """
    Construye la estructura base de frames_index.
    """
    return {
        "video_id": "",
        "generated_at": "",
        "frames": frames_metadata
    }
'@;

    ".\src\analysis\capture_selector.py" = @'
def select_captures(steps, frames_index):
    """
    Selecciona capturas representativas por paso.
    """
    return {
        "video_id": "",
        "captures": []
    }
'@;

    ".\src\qa\validator_timeline.py" = @'
def validate_timeline(timeline_data):
    """
    Valida estructura y consistencia mínima del timeline.
    """
    return []
'@
}

foreach ($file in $pythonFiles.Keys) {
    if (-not (Test-Path $file)) {
        $pythonFiles[$file] | Set-Content -Path $file -Encoding UTF8
        Write-Host "Creado: $file" -ForegroundColor Green
    }
    else {
        Write-Host "Ya existe: $file" -ForegroundColor DarkYellow
    }
}

# -------------------------------------------------
# 6. Crear manifest de corrida de ejemplo
# -------------------------------------------------
$runManifest = ".\runs\_template_run\run_manifest.json"
if (-not (Test-Path $runManifest)) {
@'
{
  "run_id": "",
  "video_source": "",
  "video_hash": "",
  "started_at": "",
  "finished_at": "",
  "pipeline_version": "",
  "prompt_versions": {},
  "settings_snapshot": {},
  "status": "pending"
}
'@ | Set-Content -Path $runManifest -Encoding UTF8
    Write-Host "Creado: $runManifest" -ForegroundColor Green
}
else {
    Write-Host "Ya existe: $runManifest" -ForegroundColor DarkYellow
}

# -------------------------------------------------
# 7. Crear archivos .gitkeep donde convenga
# -------------------------------------------------
$gitkeepDirs = @(
    ".\runs",
    ".\runs\_template_run\frames",
    ".\runs\_template_run\frames_index",
    ".\runs\_template_run\events_raw",
    ".\runs\_template_run\timeline_raw",
    ".\runs\_template_run\steps_normalized",
    ".\runs\_template_run\capture_plan",
    ".\runs\_template_run\reports",
    ".\runs\_template_run\guides",
    ".\runs\_template_run\logs"
)

foreach ($dir in $gitkeepDirs) {
    $gitkeep = Join-Path $dir ".gitkeep"
    if (-not (Test-Path $gitkeep)) {
        New-Item -ItemType File -Path $gitkeep | Out-Null
        Write-Host "Creado: $gitkeep" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Actualización completada." -ForegroundColor Cyan
Write-Host "Siguiente paso recomendado: revisar manualmente los archivos creados y luego hacer commit." -ForegroundColor White