"""Independent cold-process reproducibility check for the sixteen allowed evidence states."""
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def decode():
    import torch
    sys.path.insert(0, str(ROOT / "backend"))
    from app.local_brief import compose
    torch.set_num_threads(4)
    result = []
    for watch, alert, high in itertools.product(("aktual", "kosong", "simulasi", "tertunda"), (False, True), (False, True)):
        state = dict(watch=watch, alert=alert, ldl_high=high)
        result.append(dict(state=state, pattern=compose(state, "NAME", "FACTS")))
    print(json.dumps(result))


def compare():
    interpreter = os.environ.get("JAGSI_LLM_PYTHON", ROOT / ".venv-llm/Scripts/python.exe")
    cmd = [str(interpreter), __file__, "--decode"]
    env = dict(os.environ, HF_HUB_OFFLINE="1", HF_HOME=str(ROOT / "backend/data/llm/tmp"))
    runs = [json.loads(subprocess.check_output(cmd, env=env, text=True)) for _ in range(2)]
    same = [a == b for a, b in zip(*runs, strict=True)]
    target = ROOT / "docs/evidence/daily-brief-cold-replay.json"
    target.write_text(json.dumps(dict(matches=same, runs=runs), indent=2), encoding="utf-8")
    print(f"{sum(same)}/{len(same)} independently decoded patterns identical")
    return not all(same)


if __name__ == "__main__":
    if "--decode" in sys.argv:
        decode()
    else:
        sys.exit(compare())
