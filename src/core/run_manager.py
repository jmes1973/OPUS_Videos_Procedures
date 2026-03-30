from pathlib import Path
from datetime import datetime

def create_run_dir(base_dir: Path) -> Path:
    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
