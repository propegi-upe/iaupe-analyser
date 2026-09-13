"""
Garante que a raiz do projeto (e a pasta sandbox/, usada por alguns testes)
estejam no sys.path, do mesmo jeito que sandbox/import_docentes_interesse.py
ja faz para os scripts de producao. Sem isso, `import pipeline...` e
`import import_docentes_interesse` falhariam dependendo de onde o pytest e
chamado.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = PROJECT_ROOT / "pipeline"
SANDBOX_DIR = PROJECT_ROOT / "sandbox"

# PROJECT_ROOT: para imports absolutos "pipeline.xxx" (usados por scripts
# externos, ex.: sandbox/import_docentes_interesse.py).
# PIPELINE_DIR: os modulos DENTRO de pipeline/ (orchestration/, db/, emails/)
# importam uns aos outros como "db.xxx"/"orchestration.xxx", assumindo que
# pipeline/ e o proprio topo do sys.path - e o que acontece quando main.py e
# rodado com `python main.py` de dentro da pasta pipeline/.
for path in (PROJECT_ROOT, PIPELINE_DIR, SANDBOX_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
