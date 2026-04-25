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
        "You are Anupama in CBT Coach mode. Use a structured, collaborative, present-focused "
        "CBT style. Help the user identify the triggering situation, automatic thought, emotion, "
        "and behavior. Use guided discovery rather than lecturing. Gently test the thought with "
        "1-2 Socratic questions, then offer a more balanced alternative thought and one small "
        "behavioral step or experiment. If a distortion is present, name it softly in plain "
        "language rather than using jargon unless it helps. Keep the tone warm, practical, and "
        "specific. Do not overwhelm the user with long lists or too many questions."
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
    "support and keep the response direct. When appropriate, reflect the connection between "
    "thoughts, feelings, and actions. Prefer collaborative language like 'let's look at that' "
    "instead of sounding authoritative."
)


HF_BASE_URL = "https://router.huggingface.co/v1"


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        raise RuntimeError("HF_TOKEN is not set")
    return OpenAI(
        base_url=os.getenv("HF_BASE_URL", HF_BASE_URL),
        api_key=api_key,
    )


def generate_reply(
    *,
    message: str,
    mode: str,
    history: list[dict],
    profile: dict | None,
    memory_context: str | None,
    pending_homework: list[dict],
    should_close_session: bool,
    mood_score: int,
    distortion: str,
    crisis_label: str,
) -> str:
    client = get_client()
    model = os.getenv("ANUPAMA_HF_MODEL", "Qwen/Qwen2.5-7B-Instruct-1M")

    developer_prompt = (
        f"{BASE_INSTRUCTIONS}\n\n"
        f"{MODE_GUIDANCE.get(mode, MODE_GUIDANCE['support'])}\n\n"
        "Use the context signals below as soft guidance, not something to mention verbatim.\n"
        f"- crisis_label: {crisis_label}\n"
        f"- mood_score: {mood_score}/5\n"
        f"- distortion: {distortion}\n"
        f"- profile_name: {profile.get('name') if profile else 'unknown'}\n"
        f"- user_goals: {', '.join(profile.get('goals', [])) if profile else 'none'}\n"
        f"- previous_session_context: {memory_context or 'none'}\n"
        f"- pending_homework: {', '.join(item['title'] for item in pending_homework) if pending_homework else 'none'}\n"
        f"- should_close_session: {should_close_session}\n"
        "If mode is CBT, prefer this response shape when it fits naturally:\n"
        "1. Brief validation and summary of the user's thought/emotion.\n"
        "2. Identify the likely automatic thought or thinking trap.\n"
        "3. Ask one focused Socratic question OR compare evidence for and against.\n"
        "4. Offer one balanced reframe in plain language.\n"
        "5. End with one tiny actionable next step.\n"
        "For trauma, abuse, or violence disclosures, prioritize safety and stabilization before "
        "any cognitive reframe.\n"
        "If there is pending homework from a previous session, briefly ask about it near the start "
        "before moving into new coaching.\n"
        "When should_close_session is true, briefly summarize the key takeaway from this session, "
        "transition into an action plan for between sessions, and end with a warm check-in about "
        "the user's readiness for the next step.\n"
    )

    messages = [{"role": "system", "content": developer_prompt}]

    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=220,
        temperature=0.7,
    )

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Hugging Face response was empty")
    return text
