"""LLM structured extraction via Claude, with a disk cache keyed by a hash
of the exact prompt -- runs 2 through N of the same input are free and
instant, which matters because you'll re-run this pipeline repeatedly while
debugging the Phase 5 evaluation code."""
import os, json, hashlib, pathlib, re
import anthropic
from dotenv import load_dotenv
from src.extract.base import Extractor
from src.schema import LeaseFields, FIELDS

load_dotenv()
CACHE = pathlib.Path(".cache/llm"); CACHE.mkdir(parents=True, exist_ok=True)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-5"

SYSTEM = f"""You extract structured data from commercial lease agreements.
Return ONLY a JSON object with exactly these keys: {FIELDS}.
Rules:
- Use null when a value is NOT STATED in the text. Never guess or infer.
- base_rent_amount: base/minimum rent only. Exclude deposits, TMI/CAM, taxes,
  insurance, utilities, percentage rent. Escalating schedule -> year 1 amount.
- Dates as ISO YYYY-MM-DD. Amounts as numbers, no currency symbols or commas.
- term_length_months: initial term only, excluding renewal options.
- property_type one of: residential, commercial, retail, industrial, other.
- rent_frequency one of: monthly, annual, weekly, other.
- If the document is a lease amendment that does not restate a field
  (e.g. rent), leave that field null rather than inferring from context.
No prose, no markdown fences."""


def chunk(text: str, head=8000, tail=3000, win=3000, max_chars=24000) -> str:
    """Head + tail are reserved unconditionally before keyword windows get
    any budget. Checked empirically against this corpus: canonical first
    mentions of rent/sqft/commencement cluster in the first ~10% of a
    document, while signature blocks and closing/rider terms cluster in the
    last ~10% -- a head-plus-keyword-only chunker (the original version)
    could have that tail starved out entirely, since "rent"/"Landlord"
    repeat densely through the middle and can fill the budget first.
    """
    parts = [text[:head]]
    if len(text) > head + tail:
        parts.append(text[-tail:])
    budget = max_chars - sum(map(len, parts))
    for m in re.finditer(r"\b(base rent|monthly rent|annual rent|square feet|term of)\b", text, re.I):
        if budget <= 0:
            break
        if head < m.start() < len(text) - tail:   # skip windows already covered by head/tail
            window = text[max(0, m.start() - win // 2): m.start() + win // 2]
            parts.append(window)
            budget -= len(window)
    return "\n\n---\n\n".join(parts)[:max_chars]


class LLMExtractor(Extractor):
    name = "llm_structured"

    def extract(self, text: str) -> LeaseFields:
        payload = chunk(text)
        key = hashlib.sha256((MODEL + SYSTEM + payload).encode()).hexdigest()[:24]
        cached = CACHE / f"{key}.json"
        if cached.exists():
            return LeaseFields(**json.loads(cached.read_text()))

        msg = client.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM,
            messages=[{"role": "user", "content": payload}],
        )
        raw = "".join(b.text for b in msg.content if b.type == "text")
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
        try:
            data = {k: v for k, v in json.loads(raw).items() if k in FIELDS}
        except json.JSONDecodeError:
            data = {}
        cached.write_text(json.dumps(data))
        return LeaseFields(**data)
