"""Train a reproducible local causal-LM adapter on synthetic caregiver briefs."""
import itertools
import json
import random
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.local_brief import ROOT, plans, prompt


def main():
    random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(4)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    base = ROOT / "base"
    tok = AutoTokenizer.from_pretrained(base, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True, torch_dtype=dtype).to(device)
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"],
                                            task_type="CAUSAL_LM"))
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=0.0003)
    train, test = [], []
    for i, (watch, alert, ldl) in enumerate(itertools.product(
            ["aktual", "simulasi", "tertunda", "kosong"], [False, True], [False, True])):
        state = dict(watch=watch, alert=alert, ldl_high=ldl)
        prefix = prompt(tok, state)
        target = tok.encode(plans(state)[0], add_special_tokens=False) + [tok.eos_token_id]
        ids = torch.tensor([prefix + target], device=device)
        labels = ids.clone()
        labels[:, :len(prefix)] = -100
        (test if i in (1, 6, 11, 12) else train).append((ids, labels))

    def evaluate():
        model.eval()
        with torch.no_grad():
            return sum(model(x, labels=y, use_cache=False).loss.item() for x, y in test) / len(test)

    initial = evaluate()
    losses = []
    for epoch in range(3):
        model.train()
        random.shuffle(train)
        total = 0
        for x, y in train:
            opt.zero_grad()
            loss = model(x, labels=y, use_cache=False).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += loss.item()
        losses.append(total / len(train))
        print(f"Epoch {epoch + 1}: {losses[-1]:.3f}", flush=True)
    final = evaluate()
    model.save_pretrained(ROOT / "adapter")
    report = dict(device=device, seed=42, train_cases=len(train), holdout_cases=len(test),
                  parameters=model.get_nb_trainable_parameters()[0], epoch_losses=losses,
                  initial_holdout_loss=initial, final_holdout_loss=final)
    (ROOT / "adapter" / "evaluation.json").write_text(json.dumps(report, indent=2))
    print(report)


if __name__ == "__main__":
    main()
