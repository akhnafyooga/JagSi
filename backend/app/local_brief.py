"""Local-only, bounded language generation for Indonesian caregiver briefs."""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "llm"
SYSTEM = ("Tulis ringkasan harian keluarga dalam poin. Pertahankan placeholder NAME dan FACTS. "
          "Dahulukan peringatan aktif. Sesuaikan langkah dengan sumber bacaan dan tanda LDL.")
MODEL_ID = "JagSi-Brief-Qwen-0.5B-LoRA-v1"


def plans(state):
    starts = ["- **Kabar NAME.** FACTS", "- **Catatan harian NAME.** FACTS"]
    if state["alert"]:
        ends = ["- **Langkah sekarang.** Segera cek keadaan NAME dan buka rincian peringatan."]
    else:
        limited = state["watch"] != "aktual"
        habits = (["Tanyakan bagaimana perasaan NAME sebelum merencanakan aktivitas hari ini.",
                   "Awali hari dengan menanyakan kabar NAME secara langsung."] if limited else
                  ["Catat aktivitas NAME saat jam mengambil bacaan agar hasilnya lebih mudah dibandingkan.",
                   "Tandai apakah NAME sedang duduk atau bergerak saat pengukuran."])
        meal = ("Jika sesuai dengan anjuran makan NAME, pilih tahu kukus atau pepes ikan sebagai "
                "pengganti daging berlemak. Bahas hasil LDL saat kontrol berikutnya."
                if state["ldl_high"] else
                "Ikuti anjuran makan yang sudah diberikan kepada NAME. Belum ada dasar untuk pantangan tambahan.")
        ends = [f"- **Kebiasaan hari ini.** {habit}\n- **Pilihan makan.** {meal}" for habit in habits]
    return [start + "\n" + end for start in starts for end in ends]


def prompt(tokenizer, state):
    return tokenizer.apply_chat_template([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(state, ensure_ascii=False)},
    ], tokenize=True, add_generation_prompt=True)


@lru_cache(maxsize=1)
def load_local():
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    base = ROOT / "base"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(base, local_files_only=True,
            torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32).to(device)
    model = PeftModel.from_pretrained(model, ROOT / "adapter", local_files_only=True)
    return tok, model.eval()


def compose(state, wearer, facts):
    """Greedy constrained decoding. Fast-forward tokens shared by all legal completions."""
    import torch
    tok, model = load_local()
    prefix = prompt(tok, state)
    candidates = plans(state)
    sequences = [(tok.encode(text, add_special_tokens=False) + [tok.eos_token_id], text)
                 for text in candidates]
    generated = []
    with torch.inference_mode():
        while len(sequences) > 1:
            position = len(generated)
            options = sorted({tokens[position] for tokens, _ in sequences})
            if len(options) == 1:
                token = options[0]
            else:
                ids = torch.tensor([prefix + generated], device=model.device)
                logits = model(ids).logits[0, -1]
                token = options[int(logits[options].argmax())]
            generated.append(token)
            sequences = [(tokens, text) for tokens, text in sequences if tokens[position] == token]
    return sequences[0][1].replace("NAME", wearer).replace("FACTS", facts)