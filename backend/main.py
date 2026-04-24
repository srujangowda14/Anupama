import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from model.engine import Anupama
from backend.openai_responder import generate_reply


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHECKPOINT_DIR = ROOT_DIR / "checkpoints"


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1)
    mode: Literal["support", "cbt", "intake"] = "support"


class MoodLogRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    note: str | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    mode: Literal["support", "cbt", "intake"] | None = None
    mood_score: int | None = None
    distortion: str | None = None
    is_crisis: bool | None = None


class SessionState(BaseModel):
    id: str
    created_at: str
    history: list[ChatTurn] = Field(default_factory=list)
    mood_log: list[dict] = Field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_summary(session: SessionState) -> str:
    user_messages = [turn.content for turn in session.history if turn.role == "user"]
    assistant_messages = [turn for turn in session.history if turn.role == "assistant"]
    latest_mode = next((turn.mode for turn in reversed(session.history) if turn.mode), "support")
    latest_assistant = assistant_messages[-1] if assistant_messages else None
    mood_values = [entry["score"] for entry in session.mood_log if isinstance(entry.get("score"), int)]

    average_mood = round(sum(mood_values) / len(mood_values), 1) if mood_values else None
    recent_concerns = "\n".join(f"- {message}" for message in user_messages[-3:]) or "- No user messages recorded yet."

    key_findings = []
    if latest_assistant and latest_assistant.mood_score is not None:
        key_findings.append(f"- Latest detected mood score: {latest_assistant.mood_score}/5")
    if average_mood is not None:
        key_findings.append(f"- Average logged mood: {average_mood}/5")
    if latest_assistant and latest_assistant.distortion:
        key_findings.append(f"- Most recent cognitive distortion signal: {latest_assistant.distortion}")
    if latest_assistant and latest_assistant.is_crisis:
        key_findings.append("- Crisis protocol was triggered during this session.")
    if not key_findings:
        key_findings.append("- No classifier findings are available yet.")

    return (
        "Session Overview\n"
        f"- Session ID: {session.id}\n"
        f"- Conversation mode: {latest_mode}\n"
        f"- Messages exchanged: {len(session.history)}\n"
        f"- Created at: {session.created_at}\n\n"
        "Recent Concerns\n"
        f"{recent_concerns}\n\n"
        "Clinical Signals\n"
        f"{chr(10).join(key_findings)}\n\n"
        "Next-Step Note\n"
        "- This summary is informational only and should be reviewed by a qualified clinician."
    )


def get_allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "*")
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def load_engine() -> Anupama:
    checkpoint_dir = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))
    if not checkpoint_dir.exists():
        raise RuntimeError(
            f"Checkpoint directory not found: {checkpoint_dir}. "
            "Set MINDFUL_CHECKPOINT_DIR to the folder containing vocab.pkl and model weights."
        )

    required = ["vocab.pkl", "embed_matrix.npy"]
    missing = [name for name in required if not (checkpoint_dir / name).exists()]
    has_model = any((checkpoint_dir / name).exists() for name in ("best_model.pt", "final_model.pt"))
    if missing or not has_model:
        raise RuntimeError(
            "Checkpoint directory is incomplete. Expected vocab.pkl, embed_matrix.npy, "
            "and either best_model.pt or final_model.pt."
        )

    device = os.getenv("MODEL_DEVICE", "auto")
    return Anupama.load(str(checkpoint_dir), device_str=device)


app = FastAPI(title="Anupama API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, SessionState] = {}


@app.get("/")
def root():
    return {
        "name": "Anupama API",
        "status": "ok",
        "health": "/health",
    }


@app.get("/health")
def health():
    checkpoint_dir = Path(os.getenv("MINDFUL_CHECKPOINT_DIR", DEFAULT_CHECKPOINT_DIR))
    model_ready = checkpoint_dir.exists() and any(
        (checkpoint_dir / name).exists()
        for name in ("best_model.pt", "final_model.pt")
    )
    return {
        "status": "ok",
        "model_ready": bool(model_ready),
        "hf_ready": bool(os.getenv("HF_TOKEN")),
        "llm_provider": "huggingface",
        "checkpoint_dir": str(checkpoint_dir),
        "timestamp": utc_now(),
    }


@app.post("/chat")
def chat(payload: ChatRequest):
    try:
        engine = load_engine()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_id = payload.session_id or str(uuid4())
    session = SESSIONS.get(session_id)
    if session is None:
        session = SessionState(id=session_id, created_at=utc_now())
        SESSIONS[session_id] = session

    user_turn = ChatTurn(
        role="user",
        content=payload.message.strip(),
        timestamp=utc_now(),
        mode=payload.mode,
    )
    session.history.append(user_turn)

    classification = engine.classify(payload.message.strip())
    is_crisis = classification.crisis_label == "crisis"
    conditioning_tokens = engine._build_cond_tokens(classification, payload.mode) if not is_crisis else []

    if is_crisis:
        reply_text = engine.CRISIS_PROTOCOL
    else:
        try:
            reply_text = generate_reply(
                message=payload.message.strip(),
                mode=payload.mode,
                history=[turn.model_dump() for turn in session.history[:-1]],
                mood_score=classification.mood_score,
                distortion=classification.distortion,
                crisis_label=classification.crisis_label,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Hugging Face generation failed: {exc}") from exc

    assistant_turn = ChatTurn(
        role="assistant",
        content=reply_text,
        timestamp=utc_now(),
        mode=payload.mode,
        mood_score=classification.mood_score,
        distortion=classification.distortion,
        is_crisis=is_crisis,
    )
    session.history.append(assistant_turn)

    return {
        "session_id": session_id,
        "reply": reply_text,
        "timestamp": assistant_turn.timestamp,
        "is_crisis": is_crisis,
        "mood_score": classification.mood_score,
        "valence": classification.valence,
        "distortion": classification.distortion,
        "crisis_label": classification.crisis_label,
        "conditioning_tokens": conditioning_tokens,
    }


@app.post("/mood/{session_id}")
def log_mood(session_id: str, payload: MoodLogRequest):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    entry = {
        "score": payload.score,
        "note": payload.note,
        "timestamp": utc_now(),
    }
    session.mood_log.append(entry)
    return {"session_id": session_id, "mood_log": session.mood_log}


@app.get("/mood/{session_id}")
def get_mood(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "mood_log": session.mood_log}


@app.get("/summary/{session_id}")
def get_summary(session_id: str):
    session = SESSIONS.get(session_id)
    if session is None or not session.history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "summary": build_summary(session)}


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    session = SESSIONS.pop(session_id, None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}
