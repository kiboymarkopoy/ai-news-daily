"""Named-entity recognition for AI news headlines.

Provides a curated lookup table of ~80 AI/tech-relevant organizations,
products, people, and policy actors, plus a lightweight WHO/WHAT extractor
used by the dedup pipeline.
"""

import re

from kiboy.utils import normalize_headline

# ---------------------------------------------------------------------------
# Curated entity list — sorted by key length *descending* so the first
# match is always the longest (most specific).
# ---------------------------------------------------------------------------

KNOWN_ORGS: list[tuple[str, str]] = sorted(
    [
        # ── AI labs & companies ──────────────────────────────────────────
        ("anthropic", "Anthropic"),
        ("openai", "OpenAI"),
        ("google deepmind", "Google DeepMind"),
        ("deepmind", "DeepMind"),
        ("google", "Google"),
        ("microsoft research", "Microsoft Research"),
        ("microsoft", "Microsoft"),
        ("meta ai", "Meta AI"),
        ("meta", "Meta"),
        ("apple", "Apple"),
        ("amazon", "Amazon"),
        ("nvidia", "Nvidia"),
        ("intel", "Intel"),
        ("amd", "AMD"),
        ("ibm", "IBM"),
        ("oracle", "Oracle"),
        ("salesforce", "Salesforce"),
        ("adobe", "Adobe"),
        ("palantir", "Palantir"),
        ("databricks", "Databricks"),
        ("snowflake", "Snowflake"),
        ("mistral ai", "Mistral AI"),
        ("mistral", "Mistral"),
        ("deepseek", "DeepSeek"),
        ("stability ai", "Stability AI"),
        ("hugging face", "Hugging Face"),
        ("elevenlabs", "ElevenLabs"),
        ("character.ai", "Character.AI"),
        ("midjourney", "Midjourney"),
        ("runway", "Runway"),
        ("perplexity", "Perplexity"),
        ("groq", "Groq"),
        ("cerebras", "Cerebras"),
        ("cohere", "Cohere"),
        ("inflection", "Inflection"),
        ("minimax", "MiniMax"),
        ("xai", "xAI"),

        # ── Big tech / hardware ──────────────────────────────────────────
        ("alphabet", "Alphabet"),
        ("samsung", "Samsung"),
        ("qualcomm", "Qualcomm"),
        ("broadcom", "Broadcom"),
        ("tsmc", "TSMC"),
        ("arm", "ARM"),
        ("micron", "Micron"),
        ("sk hynix", "SK Hynix"),
        ("asml", "ASML"),
        ("dell", "Dell"),
        ("hpe", "HPE"),
        ("cisco", "Cisco"),
        ("github", "GitHub"),
        ("supermicro", "Supermicro"),

        # ── Automotive / mobility ────────────────────────────────────────
        ("tesla", "Tesla"),
        ("spacex", "SpaceX"),
        ("waymo", "Waymo"),
        ("general motors", "General Motors"),
        ("toyota", "Toyota"),
        ("byd", "BYD"),
        ("xpeng", "XPeng"),

        # ── Robotics ────────────────────────────────────────────────────
        ("boston dynamics", "Boston Dynamics"),
        ("figure ai", "Figure AI"),
        ("figure", "Figure"),
        ("unitree", "Unitree"),
        ("agility robotics", "Agility Robotics"),
        ("apptronik", "Apptronik"),
        ("1x technologies", "1X Technologies"),

        # ── Chinese AI ecosystem ────────────────────────────────────────
        ("bytedance", "ByteDance"),
        ("tencent", "Tencent"),
        ("alibaba", "Alibaba"),
        ("baidu", "Baidu"),
        ("huawei", "Huawei"),

        # ── Key people ──────────────────────────────────────────────────
        ("sam altman", "Sam Altman"),
        ("jensen huang", "Jensen Huang"),
        ("elon musk", "Elon Musk"),
        ("mark zuckerberg", "Mark Zuckerberg"),
        ("satya nadella", "Satya Nadella"),
        ("sundar pichai", "Sundar Pichai"),
        ("tim cook", "Tim Cook"),
        ("demis hassabis", "Demis Hassabis"),
        ("geoffrey hinton", "Geoffrey Hinton"),
        ("yann lecun", "Yann LeCun"),
        ("mustafa suleyman", "Mustafa Suleyman"),
        ("dario amodei", "Dario Amodei"),

        # ── Regulators / policy ─────────────────────────────────────────
        ("european union", "EU"),
        ("eu", "EU"),
        ("nist", "NIST"),
        ("fda", "FDA"),
        ("ftc", "FTC"),
        ("sec", "SEC"),
        ("fcc", "FCC"),
        ("darpa", "DARPA"),
        ("nasa", "NASA"),
        ("white house", "White House"),
        ("pentagon", "Pentagon"),

        # ── Countries / states relevant to AI policy ────────────────────
        ("china", "China"),
        ("florida", "Florida"),
        ("california", "California"),
        ("illinois", "Illinois"),
        ("connecticut", "Connecticut"),
        ("south korea", "South Korea"),
        ("japan", "Japan"),
        ("india", "India"),

        # ── Finance / conglomerates ─────────────────────────────────────
        ("softbank", "SoftBank"),

        # ── Other notable ───────────────────────────────────────────────
        ("duckduckgo", "DuckDuckGo"),
        ("netflix", "Netflix"),
        ("spotify", "Spotify"),
        ("crowdstrike", "CrowdStrike"),
        ("trump", "Trump"),
        ("bernie sanders", "Bernie Sanders"),
        ("sanders", "Sanders"),
    ],
    key=lambda pair: len(pair[0]),
    reverse=True,
)


# ---------------------------------------------------------------------------
# Config-extensible entity table
# ---------------------------------------------------------------------------
# Built-in KNOWN_ORGS above is the baseline. Operators can add or override
# entities via ``config["entities"]["extra"]`` (a ``{key: canonical}`` map)
# without editing code — e.g. {"perplexity ai": "Perplexity AI"}.

_ACTIVE_ORGS: list[tuple[str, str]] = list(KNOWN_ORGS)


def configure_entities(config: dict) -> None:
    """Merge operator-supplied entities from *config* into the active table.

    Reads ``config["entities"]["extra"]`` — a mapping of lowercase match-key
    to canonical display name. Idempotent: rebuilds the active table from the
    built-in baseline each call, so removing a config entry takes effect on
    the next run. Keeps the longest-key-first ordering the extractor relies on.
    """
    extra = (config or {}).get("entities", {}).get("extra", {})
    merged: dict[str, str] = {key: canon for key, canon in KNOWN_ORGS}
    for key, canon in extra.items():
        if isinstance(key, str) and isinstance(canon, str) and key.strip():
            merged[key.lower().strip()] = canon.strip()

    global _ACTIVE_ORGS
    _ACTIVE_ORGS = sorted(
        merged.items(), key=lambda pair: len(pair[0]), reverse=True,
    )


# ---------------------------------------------------------------------------
# WHO / WHAT extraction
# ---------------------------------------------------------------------------

def extract_who_what(title: str) -> tuple[str, str]:
    """Extract *WHO* (organization/person) and *WHAT* (action/event) from a headline.

    Strategy:
      1. Scan ``KNOWN_ORGS`` longest-key-first; first hit = WHO.
      2. Take the text after the WHO mention, strip leading punctuation,
         and truncate to 80 chars = WHAT.
      3. If no WHAT was found, fall back to the first sentence fragment.

    Args:
        title: Raw headline text.

    Returns:
        ``(who, what)`` tuple — empty strings when not found.
    """
    title_lower = title.lower()

    # Find WHO — longest match first (list is pre-sorted)
    who = ""
    match_pos = -1
    matched_key_len = 0
    for key, canonical in _ACTIVE_ORGS:
        pos = title_lower.find(key)
        if pos >= 0:
            who = canonical
            match_pos = pos
            matched_key_len = len(key)
            break  # First match is longest due to pre-sort

    # Extract WHAT — remainder after WHO mention
    what = ""
    if who and match_pos >= 0:
        remainder = title[match_pos + matched_key_len:].strip()
        remainder = re.sub(r"^[\s,:;\-–—'\"]+", "", remainder)
        what = remainder[:80].strip()

    if not what:
        sentences = re.split(r"[.!?]", title)
        if sentences:
            what = sentences[0].strip()[:80]

    return who, what
