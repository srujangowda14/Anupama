from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode


CBT_HOMEWORK_BY_DISTORTION = {
    "all_or_nothing": (
        "Continuum exercise",
        "Write down the thought in black-and-white language, then place the situation on a 0-100 scale to find a more realistic middle ground.",
    ),
    "mind_reading": (
        "Evidence check",
        "List the evidence that supports your assumption and the evidence that does not. Then write one alternative explanation.",
    ),
    "fortune_telling": (
        "Prediction log",
        "Write your prediction, estimate how likely it feels, and later compare what actually happened.",
    ),
    "catastrophizing": (
        "Best-worst-most-likely",
        "Describe the worst-case outcome, the best-case outcome, and the most likely outcome in one short paragraph each.",
    ),
    "emotional_reasoning": (
        "Feeling vs fact check",
        "Write what you feel, then separately list the facts of the situation and notice where the two differ.",
    ),
    "should_statements": (
        "Flexible language rewrite",
        "Write down each harsh 'should', 'must', or 'have to' thought. Rewrite it using more flexible language like 'I would prefer', 'it would help if', or 'I wish'. Then notice how your emotion changes.",
    ),
    "labeling": (
        "Specific behavior, not identity",
        "Take the label you used about yourself or someone else and replace it with a specific description of the behavior or situation. Finish with one sentence that reflects the full picture rather than a global label.",
    ),
    "personalization": (
        "Responsibility pie chart",
        "List all the factors that may have contributed to the situation and assign each a rough percentage. Include circumstances, other people, timing, and chance so you can see whether you are taking too much responsibility.",
    ),
    "mental_filter": (
        "Balanced evidence log",
        "Write down the upsetting detail that stood out, then list at least three facts or moments that do not fit the negative filter. End by writing a fuller, more balanced summary of the situation.",
    ),
    "discounting_positives": (
        "Own the positive",
        "Write down one positive thing that happened or one strength you showed today. For each one, do not explain it away. Instead, write why it counts and what it says about your effort, skill, or values.",
    ),
    "none": (
        "Mood and action check-in",
        "Notice one difficult moment from today, name the emotion you felt, and write one small action that helped even a little or could help next time. Keep it simple and concrete.",
    ),
}

DEFAULT_HOMEWORK = (
    "Thought record",
    "Write the situation, your automatic thought, the emotion intensity, evidence for and against, and one more balanced thought.",
)


def suggest_cbt_homework(distortion: str) -> tuple[str, str]:
    return CBT_HOMEWORK_BY_DISTORTION.get(distortion or "", DEFAULT_HOMEWORK)


def summarize_session(*, mode: str, messages: list[dict], distortion: str | None, mood_score: int | None) -> str:
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    focus = user_messages[-1] if user_messages else "No user reflections captured yet."
    bullets = [
        f"Mode: {mode}",
        f"Primary concern: {focus}",
    ]
    if distortion and distortion != "none":
        bullets.append(f"Likely CBT pattern discussed: {distortion.replace('_', ' ')}")
    if mood_score:
        bullets.append(f"Ending mood signal: {mood_score}/5")
    return "\n".join(f"- {item}" for item in bullets)


def next_checkin_due(now_iso: str) -> str:
    now_dt = datetime.fromisoformat(now_iso)
    return (now_dt + timedelta(days=3)).isoformat()


def build_google_calendar_url(*, title: str, description: str, start_at: str, end_at: str) -> str:
    def fmt(value: str) -> str:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    params = urlencode(
        {
            "action": "TEMPLATE",
            "text": title,
            "details": description,
            "dates": f"{fmt(start_at)}/{fmt(end_at)}",
        }
    )
    return f"https://calendar.google.com/calendar/render?{params}"
