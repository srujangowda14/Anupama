# Anupama

**A custom-trained mental health conversational AI — built from scratch, no LLM APIs.**

Anupama combines a shared BiLSTM encoder with three parallel classifiers (crisis detection, mood scoring, CBT cognitive distortion tagging) whose outputs condition a seq2seq response generator with Bahdanau attention. All models are trained on public mental health datasets using pre-trained Google News Word2Vec embeddings.

---

## Architecture

```
User Input
    │
    ▼
Word2Vec Embeddings (Google News, 300d — frozen)
    │
SharedBiLSTMEncoder  (256 hidden × 2 layers, bidirectional)
   ╱          │            ╲
┌──────────┐ ┌──────────┐ ┌─────────────────┐
│  Crisis  │ │Sentiment │ │ CBT Distortion  │
│Classifier│ │Detector  │ │ Tagger          │
│          │ │          │ │                 │
│safe /    │ │mood 1–5  │ │10 distortions   │
│at_risk / │ │+ valence │ │+ none           │
│crisis    │ │regression│ │attention pooling│
└────┬─────┘ └────┬─────┘ └────────┬────────┘
     └────────────┴────────────────┘
              Conditioning tokens
   <SAFE|AT_RISK|CRISIS>  <MOOD_1–5>
   <MODE_SUPPORT|CBT|INTAKE>  <DISTORTION>
              │
   ┌──────────▼──────────┐
   │  Seq2Seq Generator  │
   │  Encoder: BiLSTM    │
   │  Decoder: LSTM      │
   │  + Bahdanau Attn    │
   │  Nucleus sampling   │
   └─────────────────────┘
```

The three classifiers run first. Their predicted labels are converted to special conditioning tokens and prepended to the decoder input — so the generator's tone is directly controlled by what the model detected in the user's message.

---

## Models

| Model | Task | Output | Key Design |
|-------|------|--------|------------|
| **CrisisClassifier** | Safety triage | `safe / at_risk / crisis` | Class-weighted CE (crisis = 5×) |
| **SentimentDetector** | Mood scoring | Score 1–5 + continuous valence | Classification + MSE regression head |
| **CBTDistortionTagger** | Cognitive distortion detection | 10 types + none | Self-attention pooling over encoder states |
| **Seq2SeqGenerator** | Response generation | Token sequence | BiLSTM encoder + LSTM decoder + Bahdanau attention + nucleus sampling (top-p = 0.92) |

All four models share a single `WordEmbedding` layer and a single `SharedBiLSTMEncoder`.

---

## Three Conversation Modes

**Support Buddy** — empathetic listening, coping exercises, journaling prompts, psychoeducation

**CBT Coach** — ABC model walkthroughs, thought records, Socratic reframing of detected distortions

**Intake Assistant** — conversational history-taking that generates a structured summary the user can share with a real clinician

---

## Project Structure

```
anupama/
├── models.py                  All 4 PyTorch model definitions
├── data/
│   └── dataset.py             Vocabulary, embedding matrix, dataset classes, data loaders
├── training/
│   └── train.py               2-phase multi-task training pipeline
├── inference/
│   └── engine.py              Inference engine — classify + generate in one call
├── evaluation/
│   └── evaluate.py            BLEU-1/2/4, Distinct-1/2, F1, MAE, Pearson r
├── backend/
│   └── main.py                FastAPI backend (fully custom model, no external LLM)
├── frontend/
│   └── Anupama.jsx            React frontend — chat UI, mood tracker, coping exercises
└── requirements.txt
```

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Download Word2Vec vectors

```bash
# ~1.5 GB — Google News vectors (300d)
wget https://s3.amazonaws.com/dl4j-distribution/GoogleNews-vectors-negative300.bin.gz
gunzip GoogleNews-vectors-negative300.bin.gz

# Or via Kaggle:
kaggle datasets download -d leadbest/googlenewsvectorsnegative300
```

### 3. Get the datasets

| Model | Dataset | Where |
|-------|---------|-------|
| Seq2seq | Counsel Chat | `nbertagnolli/counsel-chat` on HuggingFace |
| Seq2seq | Mental Health Conversations | `Amod/mental_health_counseling_conversations` |
| Seq2seq | EmpatheticDialogues | [facebookresearch/EmpatheticDialogues](https://github.com/facebookresearch/EmpatheticDialogues) |
| Crisis | CLPsych 2015/2016 shared task | Academic request |
| Sentiment | SemEval 2018 Task 1 | [semeval.github.io](https://semeval.github.io) |
| Distortion | CogDistortions | Shreevastava et al. 2021 |
| Distortion | AnnoMI | [SALT-NLP/AnnoMI](https://github.com/SALT-NLP/AnnoMI) |

---

## Training

```bash
python -m training.train \
  --w2v_path ./GoogleNews-vectors-negative300.bin \
  --counsel_chat ./data/counsel_chat.jsonl \
  --mental_health ./data/mental_health.jsonl \
  --crisis ./data/crisis.jsonl \
  --sentiment ./data/sentiment.jsonl \
  --distortion ./data/distortion.jsonl \
  --output_dir ./checkpoints \
  --epochs_cls 10 \
  --epochs_joint 20 \
  --batch_size 32
```

### Two-phase strategy

**Phase 1 — Classifiers only (epochs 1–10)**
The shared encoder is trained on the three classification tasks first. This stabilizes representations of mental health language before the generator is introduced.

**Phase 2 — Joint training (epochs 11–30)**
All four models train together. Teacher forcing decays from 0.9 → 0.1 over these epochs (curriculum learning), pushing the generator to become increasingly autonomous.

| Hardware | Phase 1 | Phase 2 | Total |
|----------|---------|---------|-------|
| GPU (T4) | ~20 min | ~2 hrs | ~2.5 hrs |
| CPU only | ~3 hrs | ~12 hrs | ~15 hrs |

---

## Inference

```python
from inference.engine import MindfulAIEngine

engine = MindfulAIEngine.load("./checkpoints")

result = engine.respond(
    "I always fail at everything. I don't know why I even try.",
    mode="cbt"
)

print(result.text)
# → "It sounds like you're being really hard on yourself right now. Let's slow down — 
#    what's a specific situation where you felt this way?"

print(result.classifiers.crisis_label)     # "safe"
print(result.classifiers.mood_score)       # 2
print(result.classifiers.distortion)       # "all_or_nothing"
print(result.conditioning_tokens)          # ["<SAFE>", "<MOOD_2>", "<MODE_CBT>", "<DISTORTION>"]
```

Crisis inputs bypass generation entirely and return hardcoded emergency resources — no latency risk, no chance the model softens the signal.

---

## API

```bash
export MINDFUL_CHECKPOINT_DIR=./checkpoints
uvicorn backend.main:app --reload --port 8000
# Docs at http://localhost:8000/docs
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message, get response + classifier metadata |
| `POST` | `/mood/{session_id}` | Log a manual mood entry |
| `GET` | `/mood/{session_id}` | Retrieve mood history |
| `GET` | `/summary/{session_id}` | Generate clinician-ready session summary |
| `DELETE` | `/session/{session_id}` | Delete all session data |

---

## Evaluation

```bash
python -m evaluation.evaluate \
  --checkpoint_dir ./checkpoints \
  --crisis ./data/crisis_test.jsonl \
  --sentiment ./data/sentiment_test.jsonl \
  --distortion ./data/distortion_test.jsonl \
  --gen_pairs ./data/counsel_chat_test.jsonl
```

| Model | Metric | Target |
|-------|--------|--------|
| Crisis classifier | Crisis-class F1 | ≥ 0.80 |
| Crisis classifier | Accuracy | ≥ 0.85 |
| Sentiment detector | Accuracy | ≥ 0.65 |
| Sentiment detector | MAE | ≤ 0.80 |
| CBT distortion | Macro-F1 | ≥ 0.55 |
| Generator | BLEU-4 | ≥ 0.08 |
| Generator | Distinct-2 | ≥ 0.60 |

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-EE4C2C?logo=pytorch&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)

- **ML:** PyTorch, Gensim (Word2Vec loading)
- **Backend:** FastAPI, Uvicorn
- **Frontend:** React, Tailwind CSS
- **Embeddings:** Google News Word2Vec (300d)
- **Datasets:** Counsel Chat, EmpatheticDialogues, CLPsych, CogDistortions, AnnoMI

---

## Safety Design

- Crisis classification runs on every message before the generator is invoked
- Crisis responses are hardcoded (no generation path) — the model cannot accidentally de-escalate a genuine crisis signal
- No diagnosis, no medication guidance — enforced by system design, not just prompting
- Session data is ephemeral by default; a `/session/{id}` DELETE endpoint supports user-initiated data removal
- Red-team test cases included in the evaluation suite (self-harm signals, delusion patterns, ambiguous distress)

---

## License

MIT — free to use, modify, and build on. If you deploy this for real users, please have a licensed clinician review the safety flows first.
