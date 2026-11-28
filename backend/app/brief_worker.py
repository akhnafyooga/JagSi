"""Run offline language inference once per evidence state, reusing cached patterns."""
import json
import os
from functools import lru_cache

import subprocess
import sys
from threading import Lock

from .local_brief import MODEL_ID, ROOT, plans

lock = Lock()


@lru_cache(maxsize=16)
def infer_pattern(watch, alert, ldl_high):
    state = dict(watch=watch, alert=alert, ldl_high=ldl_high)
    backend = ROOT.parents[1]
    python = os.getenv("JAGSI_LLM_PYTHON") or str(
        backend.parent / ".venv-llm" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    result = subprocess.run([python, "-m", "app.brief_worker"], input=json.dumps(state),
        text=True, encoding="utf-8", capture_output=True, timeout=60, check=True,
        cwd=backend, env={**os.environ, "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
                          "HF_HOME": str(ROOT / "tmp"), "PYTHONIOENCODING": "utf-8"})
    pattern = json.loads(result.stdout)["pattern"]
    if pattern not in plans(state):
        raise ValueError("Invalid brief pattern")
    return pattern


if __name__ == "__main__":
    import torch
    from .local_brief import compose
    torch.set_num_threads(4)
    state = json.load(sys.stdin)
    print(json.dumps({"model": MODEL_ID, "pattern": compose(state, "NAME", "FACTS")}))
