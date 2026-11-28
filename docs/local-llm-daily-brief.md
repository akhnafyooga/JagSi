# JagSi daily brief training and local inference

The Beranda summary posts reviewed lab rows from the current browser tab and device to the JagSi backend. The backend retrieves that device’s latest watch sample and alert context. The separate language-model process receives three fields: watch availability/source, an active alert flag and a lab-reported high-LDL flag. It returns an Indonesian bullet pattern. The backend inserts the wearer’s name, dates, original values and units. If inference fails or the pattern is incompatible with the evidence, the UI identifies the fallback as JagSi rules. The chatbot still uses its preset responses. Setting a Gemini key alone can no longer activate a provider in the backend.

## Checkpoint and training

The base is Qwen/Qwen2.5-0.5B-Instruct, distributed under Apache 2.0. JagSi trained the adapter locally on CPU with seed 42, rank 8, alpha 16, and attention query/value targets. AdamW used a learning rate of 0.0003 and a maximum gradient norm of 1. The causal language-model loss applies only to the assistant answer. Source fields and numeric measurements are copied after decoding. Decoding permits only evidence-compatible completions and uses the adapted model’s next-token logits where permitted continuations diverge.

Training enumerated 16 synthetic evidence states across four watch states, alert present/absent and high LDL present/absent. Twelve combinations were used for training and four for evaluation. The splits share wording and evidence rules. Each state has one training reference. The model learned Indonesian output structure on this small dataset. The experiment does not estimate independent clinical performance or demonstrate superiority over the rules. There are no clinician-reviewed patient examples in this run.

| Measure | Result |
| --- | --- |
| Trainable parameters | 540,672 |
| Epochs / optimizer steps | 3 / 36 |
| Mean train loss by epoch | 2.811, 1.469, 0.835 |
| Held-out mean case loss, base → adapted | 3.707 → 0.745 |
| Base weight SHA-256 | fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe |
| Adapter weight SHA-256 | 9bdc9bc519fa59c85866dfd9642159b7d37fa949387060eb4a40045d6ac55455 |

The measured loss is teacher-forced token prediction averaged per case. It is independent of the constrained decoder. The held-out inputs reuse the training vocabulary and sentence structures. An evaluation on new people, devices and lab formats with clinically reviewed Indonesian briefs is still needed. The model cannot infer a medical diagnosis, personalize a diet from arbitrary analytes or measure day-long stability from one sample. Specific meal substitutions currently require a confirmed high LDL flag. Routine suggestions are suppressed during an active device alert.

## Reproduce on Windows

Run from the repository root. The supplied workspace already has the interpreter, base and adapter. On a new machine, create a Python 3.12 virtual environment named .venv-llm, install CPU PyTorch and backend/requirements-local-llm.txt, then place config.json, tokenizer.json, tokenizer_config.json, model.safetensors and LICENSE from the [official base checkpoint](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/main) in backend/data/llm/base. Verify the base hash above before training. Training and inference use local files exclusively.

~~~powershell
$env:HF_HUB_OFFLINE = '1'
$env:HF_HOME = "$PWD/backend/data/llm/tmp"
.venv-llm/Scripts/python backend/ml/train_local_brief.py
$env:PYTHONPATH = 'backend'
.venv/Scripts/python backend/ml/smoke_local_brief.py
~~~

The normal JagSi API launches an offline worker through standard input and output. No model port is required. Accepted patterns are cached across requests for the same evidence state. Set JAGSI_LLM_PYTHON if the inference interpreter is outside the default .venv-llm path. Start the JagSi API and frontend normally. In the single-device demo, confirm sample MCU rows and choose Continue, then open Beranda. Choose Perbarui ringkasan after changing a watch scenario. Confirm the card displays JagSi-Brief-Qwen-0.5B-LoRA-v1. Choosing No results available clears the tab's reviewed report when continuing setup. Watch and lab flags use the demo’s existing evidence conventions. The lab-report review and wearer linkage are single-device preview features. Before multi-user deployment, enforce authenticated device membership and verified wearer/report association server-side.

Archive backend/data/llm/adapter with its evaluation.json and base-model license for deployment. The local weights under backend/data are excluded from Git.
