# ─────────────────────────────────────────────────
# PRE-SCORE ENGINE  ·  Phase 4
# Predicts reel performance BEFORE filming
# Score = 4 components × 25 pts each = 100 pts max
# ─────────────────────────────────────────────────

from diagnostic_engine import HOOK_TRIGGERS

# ── Component 1: Duration Fit ──────────────────────────────
# Optimal duration varies by content category

DURATION_SCORES = {
    "Educational": [
        (0,  15,  8),   # Too short — no time to teach
        (15, 30, 16),   # Short but doable
        (30, 60, 25),   # Sweet spot
        (60, 90, 20),   # Fine for deep content
        (90, 999, 12),  # Risky — most drop off
    ],
    "Inspirational": [
        (0,  15, 12),
        (15, 30, 25),   # Sweet spot — punchy and emotive
        (30, 60, 22),
        (60, 90, 14),
        (90, 999, 7),
    ],
    "Transactional": [
        (0,  15, 20),
        (15, 45, 25),   # Sweet spot — quick sell
        (45, 60, 18),
        (60, 90, 10),
        (90, 999, 5),
    ],
    "Aesthetic": [
        (0,  15, 25),   # Sweet spot — pure visual, short
        (15, 30, 22),
        (30, 60, 14),
        (60, 90, 8),
        (90, 999, 4),
    ],
    "Entertainment": [
        (0,  15, 22),
        (15, 30, 25),   # Sweet spot
        (30, 60, 18),
        (60, 90, 10),
        (90, 999, 4),
    ],
}

# ── Component 2: Hook Type Power ──────────────────────────
# Intrinsic power of each hook type to stop the scroll

HOOK_POWER = {
    "Question":             24,
    "Tutorial / How-To":    23,
    "Bold Statement":       22,
    "Story / Narrative":    20,
    "Challenge / Trend":    19,
    "Behind the Scenes":    16,
    "No Hook Planned":       7,
}

# ── Component 3: Category × Hook Alignment ────────────────
# How well does this hook type fit this category?

ALIGNMENT_MATRIX = {
    "Educational": {
        "Question":          24,
        "Tutorial / How-To": 25,
        "Bold Statement":    18,
        "Story / Narrative": 16,
        "Challenge / Trend": 12,
        "Behind the Scenes": 10,
        "No Hook Planned":    6,
    },
    "Inspirational": {
        "Question":          20,
        "Tutorial / How-To": 14,
        "Bold Statement":    24,
        "Story / Narrative": 25,
        "Challenge / Trend": 16,
        "Behind the Scenes": 18,
        "No Hook Planned":    6,
    },
    "Transactional": {
        "Question":          22,
        "Tutorial / How-To": 20,
        "Bold Statement":    25,
        "Story / Narrative": 16,
        "Challenge / Trend": 14,
        "Behind the Scenes": 18,
        "No Hook Planned":    6,
    },
    "Aesthetic": {
        "Question":          16,
        "Tutorial / How-To": 14,
        "Bold Statement":    20,
        "Story / Narrative": 22,
        "Challenge / Trend": 24,
        "Behind the Scenes": 25,
        "No Hook Planned":   10,
    },
    "Entertainment": {
        "Question":          20,
        "Tutorial / How-To": 14,
        "Bold Statement":    20,
        "Story / Narrative": 22,
        "Challenge / Trend": 25,
        "Behind the Scenes": 18,
        "No Hook Planned":    6,
    },
}

# ── Risk flag definitions ──────────────────────────────────
_RISK_THRESHOLDS = {
    "duration_low":  12,    # duration score below this
    "hook_power_low": 10,   # hook power score below this
    "alignment_low":  12,   # alignment score below this
    "caption_low":    8,    # caption score below this
}


def _score_duration(duration_seconds: int, category: str) -> int:
    table = DURATION_SCORES.get(category, DURATION_SCORES["Educational"])
    for lo, hi, pts in table:
        if lo <= duration_seconds < hi:
            return pts
    return 5


def _score_caption_hook(planned_caption: str) -> int:
    """
    Score the opening line of a planned caption (0–25).
    Returns 12 (neutral) if no caption provided.
    """
    if not planned_caption or not planned_caption.strip():
        return 12  # Unknown — no penalty, no bonus

    first_line = planned_caption.strip().split('\n')[0].lower()
    triggers = [t for t in HOOK_TRIGGERS if t in first_line]
    raw_score = min(len(triggers) * 2.5, 10)

    words = first_line.split()
    if len(words) > 15:
        raw_score = max(raw_score - 2, 0)

    # Scale 0–10 → 0–25
    return round((raw_score / 10) * 25)


def _build_risk_flags(
    category: str,
    hook_type: str,
    duration_seconds: int,
    planned_caption: str,
    dur_score: int,
    hook_score: int,
    align_score: int,
    cap_score: int,
) -> list[str]:
    flags = []

    if duration_seconds > 90 and category == "Entertainment":
        flags.append("Duration over 90 s is high-risk for Entertainment — most viewers drop off before the 1-minute mark.")

    if duration_seconds > 60 and category == "Aesthetic":
        flags.append("Aesthetic reels perform best under 30 s. At this length, engagement is likely to drop significantly.")

    if hook_type == "No Hook Planned":
        flags.append("No hook strategy means the algorithm sees drop-off in the first 3 s, killing reach before it starts.")

    if align_score < _RISK_THRESHOLDS["alignment_low"]:
        flags.append(f"'{hook_type}' is a weak match for {category} content — consider a Question or Tutorial hook instead.")

    if planned_caption and cap_score < _RISK_THRESHOLDS["caption_low"]:
        flags.append("Your planned caption opening lacks scroll-stopping trigger words (Why / How / Stop / Secret etc).")

    if duration_seconds < 10 and category == "Educational":
        flags.append("Under 10 s is too short to deliver educational value — aim for 30–60 s.")

    return flags


def run_pre_score(
    category: str,
    hook_type: str,
    planned_duration_seconds: int,
    follower_count: int,
    planned_caption: str = "",
) -> dict:
    """
    Run the pre-production score model.
    Returns a dict with component scores, total, label, and risk flags.
    """

    dur_score   = _score_duration(planned_duration_seconds, category)
    hook_score  = HOOK_POWER.get(hook_type, 12)
    align_score = ALIGNMENT_MATRIX.get(category, {}).get(hook_type, 12)
    cap_score   = _score_caption_hook(planned_caption)

    total = min(dur_score + hook_score + align_score + cap_score, 100)

    if total >= 80:
        label = "Strong Launch"
        colour = "good"
        summary = "Your planned reel has the ingredients for strong organic reach."
    elif total >= 60:
        label = "Solid Foundation"
        colour = "average"
        summary = "Good base — a few targeted tweaks can push this into high-performance territory."
    elif total >= 40:
        label = "Needs Work"
        colour = "poor"
        summary = "Several elements are misaligned. Address the risk flags before filming."
    else:
        label = "High Risk"
        colour = "poor"
        summary = "This combination is likely to underperform. Review all components before proceeding."

    flags = _build_risk_flags(
        category, hook_type, planned_duration_seconds, planned_caption,
        dur_score, hook_score, align_score, cap_score
    )

    return {
        "total":       total,
        "label":       label,
        "colour":      colour,
        "summary":     summary,
        "flags":       flags,
        "components": {
            "duration":  {"score": dur_score,   "label": "Duration Fit"},
            "hook":      {"score": hook_score,  "label": "Hook Power"},
            "alignment": {"score": align_score, "label": "Category Match"},
            "caption":   {"score": cap_score,   "label": "Caption Hook"},
        },
        "inputs": {
            "category":                 category,
            "hook_type":                hook_type,
            "planned_duration_seconds": planned_duration_seconds,
            "follower_count":           follower_count,
            "planned_caption":          planned_caption,
        },
    }
