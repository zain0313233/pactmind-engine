import re

# Follow-up phrasing that often refers to the prior turn without repeating the topic
_FOLLOW_UP_RE = re.compile(
  r"(?:\b(that|this|it|those|these|there)\b"
  r"|\bexplain\s+(?:more|further|again|that|this)\b"
  r"|\bwhat\s+(?:about|does\s+that\s+mean|do\s+you\s+mean)\b"
  r"|\b(?:elaborate|clarify|break\s+it\s+down|go\s+deeper|tell\s+me\s+more)\b"
  r"|\bin\s+simpler\s+terms\b"
  r"|\bcan\s+you\s+(?:clarify|expand|simplify)\b"
  r"|\bhow\s+does\s+that\s+(?:work|apply)\b"
  r"|\bwhy\s+(?:is\s+that|does\s+that)\b"
  r"|\bwhat\s+about\s+(?:the|that)\b"
  r"|\band\s+(?:what|how)\b)",
  re.IGNORECASE,
)

_AFFIRMATIVE_RE = re.compile(
  r"^(?:yes|yeah|yep|sure|ok(?:ay)?|please|go\s+on|continue|tell\s+me)\.?$",
  re.IGNORECASE,
)


def is_follow_up_question(question: str) -> bool:
  q = question.strip()
  if not q:
    return False
  if _AFFIRMATIVE_RE.match(q):
    return True
  return bool(_FOLLOW_UP_RE.search(q))


def _last_turn(history: list[dict]) -> tuple[str, str]:
  """Return (last_user_message, last_assistant_message) from history."""
  last_user = ""
  last_assistant = ""
  for turn in history:
    role = turn.get("role", "")
    content = (turn.get("content") or "").strip()
    if not content:
      continue
    if role == "user":
      last_user = content
    elif role == "assistant":
      last_assistant = content
  return last_user, last_assistant


def build_retrieval_query(question: str, history: list[dict] | None = None) -> str:
  """
  Expand short follow-ups so vector search still finds the right contract sections.
  """
  question = question.strip()
  if not history or not is_follow_up_question(question):
    return question

  last_user, last_assistant = _last_turn(history)
  if not last_user:
    return question

  if _AFFIRMATIVE_RE.match(question):
    return last_user

  parts = [last_user, question]
  if last_assistant:
    parts.append(last_assistant[:400])
  return " ".join(parts)


def format_history_summary(history: list[dict], max_turns: int = 5) -> str:
  """Compact prior-turn summary injected into the user prompt when helpful."""
  if not history:
    return ""

  lines: list[str] = []
  for turn in history[-(max_turns * 2) :]:
    role = turn.get("role", "")
    content = (turn.get("content") or "").strip()
    if not content or role not in ("user", "assistant"):
      continue
    label = "User" if role == "user" else "PactMind"
    snippet = content[:500]
    lines.append(f"{label}: {snippet}")

  if not lines:
    return ""

  return "Recent conversation (for context — do not repeat verbatim):\n" + "\n".join(lines)
