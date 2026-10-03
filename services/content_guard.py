import re

# Questions clearly outside contract / legal document analysis
_OFF_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
  (
    re.compile(
      r"\b(write|generate|create|build|code|script|program)\b.{0,40}\b(python|javascript|java|c\+\+|sql|html|css|react|node)\b",
      re.I,
    ),
    "PactMind only answers questions about your uploaded contract — not general programming requests.",
  ),
  (
    re.compile(
      r"\b(python|javascript|java|typescript|ruby|golang)\s+(code|script|function|program)\b",
      re.I,
    ),
    "I can't generate code. Ask me about clauses, obligations, or risks in this document.",
  ),
  (
    re.compile(r"\b(tell me a joke|make me laugh|write a poem|write a story)\b", re.I),
    "I'm focused on contract analysis only — not jokes or creative writing.",
  ),
  (
    re.compile(r"\b(recipe|weather|football|cricket|movie|song lyrics)\b", re.I),
    "That doesn't look related to your contract. Ask about terms, parties, dates, or risks.",
  ),
  (
    re.compile(r"\b(homework|essay|assignment|exam question)\b", re.I),
    "PactMind is for contract documents only — not school assignments.",
  ),
  (
    re.compile(
      r"\b(ignore (all )?previous|disregard (the )?instructions|you are now|act as|pretend to be)\b",
      re.I,
    ),
    "I can only analyze the contract text provided — I won't follow override instructions.",
  ),
  (
    re.compile(r"\b(hack|exploit|bypass security|malware|virus)\b", re.I),
    "I can't help with security exploits. Ask about legitimate contract terms only.",
  ),
  (
    re.compile(
      r"\b(war|invasion|missile|military|troops|airstrike|bombing|ceasefire|sanctions)\b",
      re.I,
    ),
    "PactMind only analyzes your uploaded contract — not wars, news, or world events.",
  ),
  (
    re.compile(
      r"\b(usa|u\.s\.|america|iran|iraq|russia|ukraine|israel|palestine|china|india|pakistan|north korea)\b",
      re.I,
    ),
    "That looks like a geopolitics question, not something in this contract. Ask about clauses, parties, or obligations in the document.",
  ),
  (
    re.compile(
      r"\b(tell me about|what is happening|latest news|current events|breaking news|who won|who is the president)\b",
      re.I,
    ),
    "I can only answer questions about this contract document — not general news or world events.",
  ),
  (
    re.compile(
      r"\b(election|politics|political party|prime minister|president|parliament|congress vote)\b",
      re.I,
    ),
    "PactMind is for contract analysis only — not political or news topics.",
  ),
  (
    re.compile(r"\b(bitcoin|crypto|stock price|share price|forex|sports score|who won the match)\b", re.I),
    "I can't answer market or sports questions. Ask about terms in this agreement.",
  ),
  (
    re.compile(
      r"\b(fitness|workout|gym routine|diet plan|weight loss|exercise technique)\b",
      re.I,
    ),
    "PactMind only answers contract questions — not fitness or health advice.",
  ),
  (
    re.compile(r"\b(newton|einstein|physics|thermodynamics|calculus|science law)\b", re.I),
    "That is a general science question, not about your contract document.",
  ),
  (
    re.compile(
      r"\b(beautiful|beutiful|beautful).{0,30}\b(place|palce|earth)\b",
      re.I,
    ),
    "PactMind is for contract analysis — not travel or general knowledge.",
  ),
  (
    re.compile(r"\b(most|best).{0,20}\b(place|palce|earth|destination)\b", re.I),
    "PactMind is for contract analysis — not travel or general knowledge.",
  ),
  (
    re.compile(r"\b(budget|pudget|gdp|inflation|economy today|fiscal)\b", re.I),
    "That looks like news or economics — ask about terms in this agreement instead.",
  ),
  (
    re.compile(
      r"\b(write|create|generate|build).{0,40}\b(python|pythone|javascript|programme|program|programe|code)\b",
      re.I,
    ),
    "I can't generate code. Ask me about clauses, obligations, or risks in this document.",
  ),
  (
    re.compile(
      r"\b(python|pythone|javascript)\s+(programe|programme|program|code|script)\b",
      re.I,
    ),
    "I can't generate code. Ask me about clauses, obligations, or risks in this document.",
  ),
  (
    re.compile(r"\b(can you tell me|what is the best|how do i|how to)\b", re.I),
    "Please ask a specific question about this contract document.",
  ),
]

_CONTRACT_HINT = re.compile(
  r"\b(clause|contract|agreement|party|parties|term|termination|liability|indemnif|"
  r"payment|renewal|obligation|warranty|confidential|nda|force majeure|arbitration|"
  r"governing law|section|exhibit|amendment|sign|execute|breach|notice period)\b",
  re.I,
)


def assess_question_scope(question: str) -> dict:
  """Fast rule-based gate before RAG/LLM — saves tokens on obvious abuse."""
  q = question.strip()
  if not q:
    return {"allowed": False, "reason": "question is required"}

  for pattern, reason in _OFF_TOPIC_PATTERNS[:7]:
    if pattern.search(q):
      return {"allowed": False, "reason": reason}

  # Geopolitics / news — only when the question isn't about the contract itself
  if not _CONTRACT_HINT.search(q):
    for pattern, reason in _OFF_TOPIC_PATTERNS[7:]:
      if pattern.search(q):
        return {"allowed": False, "reason": reason}

  # Very short vague prompts with no contract signal
  if len(q) < 12 and not _CONTRACT_HINT.search(q):
    vague = re.compile(
      r"^(hi|hello|hey|help|test|ok|yes|no|thanks|thank you)\.?$", re.I
    )
    if vague.match(q):
      return {
        "allowed": False,
        "reason": "Please ask a specific question about this contract document.",
      }

  if (
    re.search(r"\b(war|invasion|news|election|president|weather|sports|celebrity|recipe)\b", q, re.I)
    and not _CONTRACT_HINT.search(q)
  ):
    return {
      "allowed": False,
      "reason": (
        "That question is not about this contract. Ask about clauses, payment terms, "
        "liability, termination, or parties in the document."
      ),
    }

  if (
    re.search(r"\btell me about\b", q, re.I)
    and not _CONTRACT_HINT.search(q)
    and not re.search(r"\b(this|the)\s+(contract|agreement|document|clause)\b", q, re.I)
  ):
    return {
      "allowed": False,
      "reason": (
        "Please ask a specific question about this contract — e.g. payment terms, "
        "liability, or termination."
      ),
    }

  return {"allowed": True, "reason": None}


_MIN_RELEVANCE_SCORE = 0.40
_WEAK_RELEVANCE_SCORE = 0.50

_OFF_TOPIC_SHORT = (
  "I couldn't find anything in this contract related to your question. "
  "PactMind only answers questions about the uploaded document — "
  "not news, wars, or unrelated topics."
)


def assess_retrieval_relevance(question: str, chunks: list[dict]) -> dict:
  """Skip LLM when retrieved chunks are a poor match — saves tokens."""
  if not chunks:
    return {"relevant": False, "reason": _OFF_TOPIC_SHORT}

  top_score = max(float(c.get("score") or 0) for c in chunks)
  q = question.strip()
  has_contract_hint = bool(_CONTRACT_HINT.search(q))

  if top_score < _MIN_RELEVANCE_SCORE:
    return {"relevant": False, "reason": _OFF_TOPIC_SHORT}

  if top_score < _WEAK_RELEVANCE_SCORE and not has_contract_hint:
    return {
      "relevant": False,
      "reason": (
        "Your question doesn't look related to this contract, and I couldn't find "
        "a strong match in the document. Ask about clauses, parties, payment, "
        "liability, or termination."
      ),
    }

  return {"relevant": True, "reason": None}


  return {"relevant": True, "reason": None}


_MALICIOUS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
  (re.compile(r"<script[\s>]", re.I), "embedded script tag"),
  (re.compile(r"javascript\s*:", re.I), "javascript URI"),
  (re.compile(r"on(?:error|load|click)\s*=", re.I), "DOM event handler injection"),
  (re.compile(r"\beval\s*\(", re.I), "eval() call"),
  (re.compile(r"document\.cookie", re.I), "cookie access attempt"),
  (re.compile(r"<\?php", re.I), "PHP code"),
  (re.compile(r"\b__import__\s*\(", re.I), "Python import injection"),
  (re.compile(r"\bos\.system\s*\(", re.I), "OS command execution"),
  (re.compile(r"\bsubprocess\.", re.I), "subprocess invocation"),
  (re.compile(
    r"\b(ignore (all )?previous|disregard (the )?instructions|you are now|act as|system prompt)\b",
    re.I,
  ), "prompt-injection phrase"),
]


def security_scan_document(text: str) -> dict:
  """
  Auto security scan on upload — safe-by-default.
  Only blocks clearly malicious content; otherwise auto-approves for immediate use.
  """
  sample = text[:25_000]
  threats: list[str] = []

  for pattern, label in _MALICIOUS_PATTERNS:
    if pattern.search(sample):
      threats.append(label)

  if threats:
    return {
      "safe": False,
      "status": "rejected",
      "summary": "Malicious or unsafe content detected — document blocked pending admin review.",
      "threats": threats,
      "security_risks": threats,
      "queries_enabled": False,
      "recommendation": "block_queries",
    }

  return {
    "safe": True,
    "status": "valid",
    "summary": "Passed automated security scan. Document approved for immediate use.",
    "threats": [],
    "security_risks": [],
    "queries_enabled": True,
    "recommendation": "approve",
  }


_NON_CONTRACT_SIGNALS = [
  re.compile(p, re.I)
  for p in (
    r"\bdef\s+\w+\s*\(",  # python
    r"function\s+\w+\s*\(",
    r"import\s+(os|sys|numpy|pandas)",
    r"<\?php",
    r"#include\s*<",
    r"console\.log\(",
    r"recipe\s+for",
    r"ingredients:",
    r"preheat oven",
    r"once upon a time",
    r"lorem ipsum",
  )
]

_CONTRACT_SIGNALS = re.compile(
  r"\b(agreement|contract|party|parties|whereas|hereby|shall|liability|"
  r"indemnif|termination|confidential|governing law|effective date|"
  r"services|payment|clause|section\s+\d)\b",
  re.I,
)


def quick_document_screen(text: str) -> dict:
  """Rule-based pre-screen without LLM — used right after upload."""
  sample = text[:8000]
  non_contract_hits = sum(1 for p in _NON_CONTRACT_SIGNALS if p.search(sample))
  contract_hits = len(_CONTRACT_SIGNALS.findall(sample))

  if non_contract_hits >= 2 and contract_hits < 2:
    return {
      "status": "suspicious",
      "summary": "Content looks like code, fiction, or non-contract material.",
      "is_legal_document": False,
      "confidence": "medium",
      "security_risks": [],
      "recommendation": "Review before allowing heavy AI usage.",
    }

  if contract_hits >= 3:
    return {
      "status": "valid",
      "summary": "Document contains typical contract language.",
      "is_legal_document": True,
      "confidence": "medium",
      "security_risks": [],
      "recommendation": "Looks like a legitimate contract document.",
    }

  return {
    "status": "pending",
    "summary": "Automatic screening inconclusive — admin review recommended.",
    "is_legal_document": None,
    "confidence": "low",
    "security_risks": [],
    "recommendation": "Run a PactMind content review from the admin panel.",
  }
