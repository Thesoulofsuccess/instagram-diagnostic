"""
competitor.py  ·  Phase 8: Industry Benchmark Comparison
─────────────────────────────────────────────────────────
Compares a creator's personal averages against 2025 Instagram Reels
industry benchmarks, broken down by follower tier and content category.

Follower tiers:
  nano   0 – 10 K
  micro  10 K – 50 K
  mid    50 K – 200 K
  macro  200 K+

Grade thresholds (delta vs benchmark):
  Crushing It  ≥ +30 %   #00E5A0
  Above Avg    ≥ +10 %   #7DFFCC
  On Par       ≥ −10 %   #FFB020
  Below Avg    ≥ −25 %   #FF8C00
  Lagging       < −25 %  #FF3D71
"""

from __future__ import annotations
import statistics

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

TIERS = ("nano", "micro", "mid", "macro")

TIER_LABELS = {
    "nano":  "Nano  (< 10 K)",
    "micro": "Micro (10 K – 50 K)",
    "mid":   "Mid   (50 K – 200 K)",
    "macro": "Macro (200 K+)",
}

# Industry benchmark data (2025 estimates)
# Keys: (category, tier)
# Values: avg_views, avg_retention (ratio 0-1), avg_engagement (ratio 0-1), avg_save_rate (ratio 0-1)
INDUSTRY_BENCHMARKS: dict[tuple[str, str], dict] = {
    # ── Educational ──────────────────────────────
    ("Educational", "nano"):  {"avg_views": 1_400,  "avg_retention": 0.54, "avg_engagement": 0.062, "avg_save_rate": 0.028},
    ("Educational", "micro"): {"avg_views": 5_200,  "avg_retention": 0.52, "avg_engagement": 0.045, "avg_save_rate": 0.022},
    ("Educational", "mid"):   {"avg_views": 18_000, "avg_retention": 0.49, "avg_engagement": 0.030, "avg_save_rate": 0.016},
    ("Educational", "macro"): {"avg_views": 65_000, "avg_retention": 0.46, "avg_engagement": 0.018, "avg_save_rate": 0.010},

    # ── Entertainment ─────────────────────────────
    ("Entertainment", "nano"):  {"avg_views": 1_800,  "avg_retention": 0.50, "avg_engagement": 0.070, "avg_save_rate": 0.020},
    ("Entertainment", "micro"): {"avg_views": 7_500,  "avg_retention": 0.47, "avg_engagement": 0.050, "avg_save_rate": 0.015},
    ("Entertainment", "mid"):   {"avg_views": 28_000, "avg_retention": 0.44, "avg_engagement": 0.032, "avg_save_rate": 0.011},
    ("Entertainment", "macro"): {"avg_views": 95_000, "avg_retention": 0.40, "avg_engagement": 0.020, "avg_save_rate": 0.007},

    # ── Inspirational ─────────────────────────────
    ("Inspirational", "nano"):  {"avg_views": 1_200,  "avg_retention": 0.48, "avg_engagement": 0.058, "avg_save_rate": 0.030},
    ("Inspirational", "micro"): {"avg_views": 4_500,  "avg_retention": 0.46, "avg_engagement": 0.042, "avg_save_rate": 0.024},
    ("Inspirational", "mid"):   {"avg_views": 16_000, "avg_retention": 0.43, "avg_engagement": 0.027, "avg_save_rate": 0.017},
    ("Inspirational", "macro"): {"avg_views": 58_000, "avg_retention": 0.40, "avg_engagement": 0.016, "avg_save_rate": 0.011},

    # ── Transactional ─────────────────────────────
    ("Transactional", "nano"):  {"avg_views": 900,    "avg_retention": 0.56, "avg_engagement": 0.050, "avg_save_rate": 0.035},
    ("Transactional", "micro"): {"avg_views": 3_500,  "avg_retention": 0.54, "avg_engagement": 0.038, "avg_save_rate": 0.028},
    ("Transactional", "mid"):   {"avg_views": 12_000, "avg_retention": 0.51, "avg_engagement": 0.025, "avg_save_rate": 0.020},
    ("Transactional", "macro"): {"avg_views": 42_000, "avg_retention": 0.48, "avg_engagement": 0.015, "avg_save_rate": 0.013},

    # ── Aesthetic ─────────────────────────────────
    ("Aesthetic", "nano"):  {"avg_views": 1_600,  "avg_retention": 0.43, "avg_engagement": 0.065, "avg_save_rate": 0.022},
    ("Aesthetic", "micro"): {"avg_views": 6_200,  "avg_retention": 0.41, "avg_engagement": 0.048, "avg_save_rate": 0.017},
    ("Aesthetic", "mid"):   {"avg_views": 22_000, "avg_retention": 0.38, "avg_engagement": 0.031, "avg_save_rate": 0.012},
    ("Aesthetic", "macro"): {"avg_views": 80_000, "avg_retention": 0.35, "avg_engagement": 0.019, "avg_save_rate": 0.008},
}

# Fallback benchmark per tier (average across categories)
_TIER_FALLBACK: dict[str, dict] = {
    "nano":  {"avg_views": 1_400,  "avg_retention": 0.50, "avg_engagement": 0.061, "avg_save_rate": 0.027},
    "micro": {"avg_views": 5_400,  "avg_retention": 0.48, "avg_engagement": 0.045, "avg_save_rate": 0.021},
    "mid":   {"avg_views": 19_200, "avg_retention": 0.45, "avg_engagement": 0.029, "avg_save_rate": 0.015},
    "macro": {"avg_views": 68_000, "avg_retention": 0.42, "avg_engagement": 0.018, "avg_save_rate": 0.010},
}

# Map any user-entered category to our 5 standard ones
_CATEGORY_NORMALISE = {
    "educational": "Educational",
    "education":   "Educational",
    "tutorial":    "Educational",
    "how-to":      "Educational",
    "tips":        "Educational",
    "entertainment": "Entertainment",
    "funny":         "Entertainment",
    "comedy":        "Entertainment",
    "trending":      "Entertainment",
    "inspirational": "Inspirational",
    "motivation":    "Inspirational",
    "motivational":  "Inspirational",
    "lifestyle":     "Inspirational",
    "transactional": "Transactional",
    "product":       "Transactional",
    "sales":         "Transactional",
    "promo":         "Transactional",
    "promotional":   "Transactional",
    "aesthetic":     "Aesthetic",
    "fashion":       "Aesthetic",
    "beauty":        "Aesthetic",
    "style":         "Aesthetic",
}


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _detect_follower_tier(follower_count: int) -> str:
    if follower_count < 10_000:
        return "nano"
    if follower_count < 50_000:
        return "micro"
    if follower_count < 200_000:
        return "mid"
    return "macro"


def _normalise_category(raw: str) -> str:
    return _CATEGORY_NORMALISE.get(raw.lower().strip(), raw.title())


def _pct_delta(user: float, benchmark: float) -> float:
    """Return % delta of user vs benchmark. Positive = above."""
    if benchmark == 0:
        return 0.0
    return ((user - benchmark) / benchmark) * 100.0


def _grade(delta_pct: float) -> tuple[str, str]:
    """Return (label, css_class) based on delta vs benchmark."""
    if delta_pct >= 30:
        return "Crushing It", "crushing"
    if delta_pct >= 10:
        return "Above Avg",   "above"
    if delta_pct >= -10:
        return "On Par",      "on_par"
    if delta_pct >= -25:
        return "Below Avg",   "below"
    return "Lagging",         "lagging"


def _score_metric(user: float, benchmark: float) -> int:
    """
    Score one metric 0–25 relative to benchmark.
    +30 % above → 25 pts, at benchmark → 12 pts, -40 % → 0 pts.
    """
    if benchmark == 0:
        return 12
    ratio = user / benchmark
    if ratio >= 1.30:
        return 25
    if ratio >= 1.0:
        return round(12.5 + (ratio - 1.0) / 0.30 * 12.5)
    if ratio >= 0.60:
        return round((ratio - 0.60) / 0.40 * 12.5)
    return 0


def _get_benchmark(category: str, tier: str) -> dict:
    key = (_normalise_category(category), tier)
    return INDUSTRY_BENCHMARKS.get(key, _TIER_FALLBACK[tier])


# ──────────────────────────────────────────────
# MAIN COMPUTE
# ──────────────────────────────────────────────

def compute_benchmark_report(reels: list[dict]) -> dict:
    """
    Build a full benchmark comparison report from the user's saved reels.

    Returns a structured dict ready for render_competitor_benchmarks().
    """
    if not reels:
        return {"has_data": False}

    # ── Auto-detect follower tier ─────────────────────────────────────────
    follower_counts = [r.get("follower_count") for r in reels if r.get("follower_count")]
    if follower_counts:
        median_fc = int(statistics.median(follower_counts))
    else:
        median_fc = 0
    tier = _detect_follower_tier(median_fc)

    # ── Overall user averages ─────────────────────────────────────────────
    user_avg_views      = _avg([r.get("views", 0)            for r in reels])
    user_avg_retention  = _avg([r["retention_ratio"]         for r in reels if r.get("retention_ratio")  is not None])
    user_avg_engagement = _avg([r["engagement_rate"]         for r in reels if r.get("engagement_rate")  is not None])
    user_avg_save_rate  = _avg([r["save_rate"]               for r in reels if r.get("save_rate")        is not None])

    # ── Determine primary category (most posted) ───────────────────────────
    from collections import Counter
    cat_counts = Counter(r.get("category", "Unknown") for r in reels)
    primary_category_raw = cat_counts.most_common(1)[0][0]
    primary_category = _normalise_category(primary_category_raw)

    # ── Overall benchmark for primary category ─────────────────────────────
    bench = _get_benchmark(primary_category, tier)
    bv  = bench["avg_views"]
    br  = bench["avg_retention"]
    be  = bench["avg_engagement"]
    bs  = bench["avg_save_rate"]

    # ── Per-metric deltas & grades ─────────────────────────────────────────
    delta_views = _pct_delta(user_avg_views,      bv)
    delta_ret   = _pct_delta(user_avg_retention,  br)
    delta_eng   = _pct_delta(user_avg_engagement, be)
    delta_save  = _pct_delta(user_avg_save_rate,  bs)

    grade_views, cls_views = _grade(delta_views)
    grade_ret,   cls_ret   = _grade(delta_ret)
    grade_eng,   cls_eng   = _grade(delta_eng)
    grade_save,  cls_save  = _grade(delta_save)

    # ── Benchmark Score (0–100) ────────────────────────────────────────────
    s_views = _score_metric(user_avg_views,      bv)
    s_ret   = _score_metric(user_avg_retention,  br)
    s_eng   = _score_metric(user_avg_engagement, be)
    s_save  = _score_metric(user_avg_save_rate,  bs)
    benchmark_score = s_views + s_ret + s_eng + s_save  # 0–100

    if benchmark_score >= 80:
        score_label, score_colour = "Industry Leader",  "crushing"
    elif benchmark_score >= 60:
        score_label, score_colour = "Above Average",    "above"
    elif benchmark_score >= 40:
        score_label, score_colour = "On Par",           "on_par"
    elif benchmark_score >= 25:
        score_label, score_colour = "Below Average",    "below"
    else:
        score_label, score_colour = "Needs Work",       "lagging"

    # ── Strongest & weakest metrics ────────────────────────────────────────
    metric_deltas = {
        "Views":      delta_views,
        "Retention":  delta_ret,
        "Engagement": delta_eng,
        "Save Rate":  delta_save,
    }
    strongest_metric  = max(metric_deltas, key=metric_deltas.get)
    strongest_delta   = metric_deltas[strongest_metric]

    # Two biggest opportunities (lowest delta metrics)
    sorted_metrics = sorted(metric_deltas.items(), key=lambda x: x[1])
    opportunity_metrics = sorted_metrics[:2]  # 2 worst

    # Build opportunity cards
    metric_bench_vals = {
        "Views":      (user_avg_views,      bv,  "views"),
        "Retention":  (user_avg_retention,  br,  "retention"),
        "Engagement": (user_avg_engagement, be,  "engagement"),
        "Save Rate":  (user_avg_save_rate,  bs,  "save_rate"),
    }
    opportunity_cards = []
    for name, delta in opportunity_metrics:
        user_val, bench_val, _ = metric_bench_vals[name]
        if name == "Views":
            user_fmt  = f"{int(user_val):,}"
            bench_fmt = f"{int(bench_val):,}"
            target    = f"{int(bench_val):,} views/reel"
        elif name in ("Retention", "Engagement", "Save Rate"):
            user_fmt  = f"{user_val * 100:.1f}%"
            bench_fmt = f"{bench_val * 100:.1f}%"
            target    = f"{bench_val * 100:.1f}% {name.lower()}"
        else:
            user_fmt  = f"{user_val:.2f}"
            bench_fmt = f"{bench_val:.2f}"
            target    = bench_fmt
        opportunity_cards.append({
            "metric":     name,
            "user_val":   user_fmt,
            "bench_val":  bench_fmt,
            "target":     target,
            "delta_pct":  round(delta, 1),
        })

    # ── Category breakdown ─────────────────────────────────────────────────
    category_breakdown = []
    for cat_raw, count in cat_counts.most_common():
        cat_reels = [r for r in reels if r.get("category") == cat_raw]
        cat_views  = _avg([r.get("views", 0) for r in cat_reels])
        cat_ret    = _avg([r["retention_ratio"]  for r in cat_reels if r.get("retention_ratio")  is not None])
        cat_eng    = _avg([r["engagement_rate"]  for r in cat_reels if r.get("engagement_rate")  is not None])

        cat_norm  = _normalise_category(cat_raw)
        cat_bench = _get_benchmark(cat_norm, tier)

        cat_delta_views = _pct_delta(cat_views, cat_bench["avg_views"])
        cat_delta_ret   = _pct_delta(cat_ret,   cat_bench["avg_retention"])
        cat_delta_eng   = _pct_delta(cat_eng,   cat_bench["avg_engagement"])

        cat_grade_views, cat_cls_views = _grade(cat_delta_views)
        cat_grade_ret,   _             = _grade(cat_delta_ret)
        cat_grade_eng,   _             = _grade(cat_delta_eng)

        category_breakdown.append({
            "category":        cat_raw,
            "count":           count,
            "avg_views":       round(cat_views),
            "bench_views":     round(cat_bench["avg_views"]),
            "delta_views":     round(cat_delta_views, 1),
            "grade_views":     cat_grade_views,
            "cls_views":       cat_cls_views,
            "avg_retention":   round(cat_ret * 100, 1),
            "bench_retention": round(cat_bench["avg_retention"] * 100, 1),
            "grade_ret":       cat_grade_ret,
            "avg_engagement":  round(cat_eng * 100, 2),
            "bench_engagement":round(cat_bench["avg_engagement"] * 100, 2),
            "grade_eng":       cat_grade_eng,
        })

    return {
        "has_data":           True,
        "reel_count":         len(reels),
        "follower_count":     median_fc,
        "tier":               tier,
        "tier_label":         TIER_LABELS[tier],
        "primary_category":   primary_category,

        # Overall user averages
        "user_avg_views":       round(user_avg_views),
        "user_avg_retention":   round(user_avg_retention * 100, 1),
        "user_avg_engagement":  round(user_avg_engagement * 100, 2),
        "user_avg_save_rate":   round(user_avg_save_rate * 100, 2),

        # Industry benchmarks (primary category)
        "bench_avg_views":       round(bv),
        "bench_avg_retention":   round(br * 100, 1),
        "bench_avg_engagement":  round(be * 100, 2),
        "bench_avg_save_rate":   round(bs * 100, 2),

        # Deltas
        "delta_views":      round(delta_views, 1),
        "delta_ret":        round(delta_ret,   1),
        "delta_eng":        round(delta_eng,   1),
        "delta_save":       round(delta_save,  1),

        # Grades
        "grade_views":  grade_views,  "cls_views":  cls_views,
        "grade_ret":    grade_ret,    "cls_ret":    cls_ret,
        "grade_eng":    grade_eng,    "cls_eng":    cls_eng,
        "grade_save":   grade_save,   "cls_save":   cls_save,

        # Score
        "benchmark_score":  benchmark_score,
        "score_label":      score_label,
        "score_colour":     score_colour,
        "score_components": {
            "views":      s_views,
            "retention":  s_ret,
            "engagement": s_eng,
            "save_rate":  s_save,
        },

        # Insights
        "strongest_metric":  strongest_metric,
        "strongest_delta":   round(strongest_delta, 1),
        "opportunity_cards": opportunity_cards,

        # Category table
        "category_breakdown": category_breakdown,
    }
