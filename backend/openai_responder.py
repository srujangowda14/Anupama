import os
from functools import lru_cache

from openai import OpenAI


MODE_GUIDANCE = {
    "support": (
        "You are Anupama in Support Buddy mode. Respond like a warm, emotionally attuned "
        "support companion. Reflect the user's feelings, avoid sounding clinical, and ask "
        "at most one gentle follow-up question."
    ),
    "cbt": (
        "You are Anupama in CBT Coach mode. Help the user notice thought patterns, challenge "
        "distortions carefully, and offer one practical CBT-style reframe or exercise. Keep "
        "the tone compassionate, not robotic."
    ),
    "intake": (
        "You are Anupama in Intake Assistant mode. Help the user organize what they are "
        "experiencing for a future therapist visit. Ask focused, supportive questions and "
        "avoid trying to solve everything at once."
    ),
}

BASE_INSTRUCTIONS = (
    "You are Anupama, a supportive mental-health-focused conversational assistant. "
    "Do not claim to be a licensed clinician. Do not provide diagnosis or medication advice. "
    "Keep answers concise, natural, and human. Avoid generic AI disclaimers unless safety truly "
    "requires them. If the user appears at immediate risk of self-harm, encourage urgent human "
    "support and keep the response direct."
)


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def generate_reply(
    *,
    message: str,
    mode: str,
    history: list[dict],
    mood_score: int,
    distortion: str,
    crisis_label: str,
) -> str:
    client = get_client()
    model = os.getenv("ANUPAMA_OPENAI_MODEL", "gpt-5")

    developer_prompt = (
        f"{BASE_INSTRUCTIONS}\n\n"
        f"{MODE_GUIDANCE.get(mode, MODE_GUIDANCE['support'])}\n\n"
        "Use the context signals below as soft guidance, not something to mention verbatim.\n"
        f"- crisis_label: {crisis_label}\n"
        f"- mood_score: {mood_score}/5\n"
        f"- distortion: {distortion}\n"
    )

    input_items = [
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": developer_prompt}],
        }
    ]

    for turn in history[-6:]:
        input_items.append(
            {
                "role": turn["role"],
                "content": [{"type": "input_text", "text": turn["content"]}],
            }
        )

    input_items.append(
        {
            "role": "user",
            "content": [{"type": "input_text", "text": message}],
        }
    )

    response = client.responses.create(
        model=model,
        input=input_items,
        max_output_tokens=220,
    )

    text = (response.output_text or "").strip()
    if not text:
        raise RuntimeError("OpenAI response was empty")
    return text
