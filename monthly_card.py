"""
monthly_card.py  ·  Phase 7: Monthly Performance Card
──────────────────────────────────────────────────────
Computes a month-over-month performance summary from the user's saved reels.
Returns a structured dict ready for the in-app card and optional PDF/screenshot.

Growth Score (0–100):
  25 pts  Views growth    vs prior month (or all-time avg)
  25 pts  Retention       vs personal average
  25 pts  Engagement rate vs personal average
  25 pts  Save rate       vs personal average
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta
from calendar import month_name


# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────

def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct_change(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def _parse_dt(r: dict):
    raw = r.get("created_at", "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _score_component(current: float, baseline: float, weight: int = 25) -> int:
    """
    Score a metric relative to its baseline.
    +20% above baseline  → full weight
    at baseline          → half weight
    -40% below baseline  → 0
    """
    if baseline == 0:
        return weight // 2
    ratio = current / baseline
    if ratio >= 1.20:
        return weight
    if ratio >= 1.0:
        # Linear: 1.0 → half, 1.2 → full
        return round(weight * 0.5 + (ratio - 1.0) / 0.20 * weight * 0.5)
    if ratio >= 0.60:
        # Linear: 0.6 → 0, 1.0 → half
        return round((ratio - 0.60) / 0.40 * weight * 0.5)
    return 0


# ─────────────────────────────────────────────────
# MAIN COMPUTE
# ─────────────────────────────────────────────────

def compute_monthly_card(reels: list[dict], target_year: int = None, target_month: int = None) -> dict:
    """
    Build a monthly performance card from all saved reels.

    target_year / target_month default to the current month.
    Falls back to all-time card if fewer than 2 reels in the target month.
    """
    now = datetime.now(timezone.utc)
    if target_year is None:
        target_year = now.year
    if target_month is None:
        target_month = now.month

    # ── Split reels into this month / last month / older ─────────────────
    this_month_reels = []
    last_month_reels = []
    all_other_reels  = []

    # Compute last month
    if target_month == 1:
        prev_year, prev_month = target_year - 1, 12
    else:
        prev_year, prev_month = target_year, target_month - 1

    for r in reels:
        dt = _parse_dt(r)
        if dt is None:
            all_other_reels.append(r)
            continue
        if dt.year == target_year and dt.month == target_month:
            this_month_reels.append(r)
        elif dt.year == prev_year and dt.month == prev_month:
            last_month_reels.append(r)
        else:
            all_other_reels.append(r)

    # If fewer than 2 reels this month, use all reels with a note
    use_all_time = len(this_month_reels) < 2
    summary_reels = reels if use_all_time else this_month_reels
    compare_reels = last_month_reels if not use_all_time else []

    if not summary_reels:
        return {"has_data": False}

    # ── Core metrics for summary period ──────────────────────────────────
    views_list      = [r.get("views", 0) for r in summary_reels]
    retention_list  = [r.get("retention_ratio", 0) for r in summary_reels if r.get("retention_ratio") is not None]
    engagement_list = [r.get("engagement_rate", 0) for r in summary_reels if r.get("engagement_rate") is not None]
    hook_list       = [r.get("hook_score", 0) for r in summary_reels if r.get("hook_score") is not None]
    save_rate_list  = [r.get("save_rate", 0) for r in summary_reels if r.get("save_rate") is not None]
    saves_list      = [r.get("saves", 0) for r in summary_reels]
    likes_list      = [r.get("likes", 0) for r in summary_reels]

    avg_views      = _avg(views_list)
    avg_retention  = _avg(retention_list)
    avg_engagement = _avg(engagement_list)
    avg_hook       = _avg(hook_list)
    avg_save_rate  = _avg(save_rate_list)
    total_views    = sum(views_list)
    total_saves    = sum(saves_list)
    total_likes    = sum(likes_list)

    # ── Baseline (prior period or all-time) ───────────────────────────────
    if compare_reels:
        baseline_views     = _avg([r.get("views", 0) for r in compare_reels])
        baseline_retention = _avg([r.get("retention_ratio", 0) for r in compare_reels if r.get("retention_ratio") is not None])
        baseline_eng       = _avg([r.get("engagement_rate", 0) for r in compare_reels if r.get("engagement_rate") is not None])
        baseline_save      = _avg([r.get("save_rate", 0) for r in compare_reels if r.get("save_rate") is not None])
    else:
        # Use global average of all other reels as baseline
        all_fallback = all_other_reels or reels
        baseline_views     = _avg([r.get("views", 0) for r in all_fallback])
        baseline_retention = _avg([r.get("retention_ratio", 0) for r in all_fallback if r.get("retention_ratio") is not None])
        baseline_eng       = _avg([r.get("engagement_rate", 0) for r in all_fallback if r.get("engagement_rate") is not None])
        baseline_save      = _avg([r.get("save_rate", 0) for r in all_fallback if r.get("save_rate") is not None])

    # ── Growth Score ──────────────────────────────────────────────────────
    s_views = _score_component(avg_views,      baseline_views,     25)
    s_ret   = _score_component(avg_retention,  baseline_retention, 25)
    s_eng   = _score_component(avg_engagement, baseline_eng,       25)
    s_save  = _score_component(avg_save_rate,  baseline_save,      25)
    growth_score = s_views + s_ret + s_eng + s_save

    if growth_score >= 80:
        score_label, score_colour = "Breakout Month",  "good"
    elif growth_score >= 60:
        score_label, score_colour = "Growing",         "good"
    elif growth_score >= 40:
        score_label, score_colour = "Steady",          "average"
    else:
        score_label, score_colour = "Needs Attention", "poor"

    # ── Month-over-month changes ──────────────────────────────────────────
    view_change = _pct_change(avg_views,      baseline_views)     if baseline_views     else None
    ret_change  = _pct_change(avg_retention,  baseline_retention) if baseline_retention else None
    eng_change  = _pct_change(avg_engagement, baseline_eng)       if baseline_eng       else None
    save_change = _pct_change(avg_save_rate,  baseline_save)      if baseline_save      else None

    # ── Most improved metric ──────────────────────────────────────────────
    changes = {
        "Views":      view_change,
        "Retention":  ret_change,
        "Engagement": eng_change,
        "Save Rate":  save_change,
    }
    valid_changes = {k: v for k, v in changes.items() if v is not None}
    most_improved  = max(valid_changes, key=lambda k: valid_changes[k]) if valid_changes else None
    most_improved_val = valid_changes.get(most_improved)

    # ── Best reel of the month ─────────────────────────────────────────────
    sorted_reels = sorted(summary_reels, key=lambda r: r.get("views", 0), reverse=True)
    best_reel    = sorted_reels[0] if sorted_reels else None

    # ── Category breakdown (sorted by avg views) ──────────────────────────
    cat_stats: dict[str, dict] = {}
    for r in summary_reels:
        cat = r.get("category") or "Uncategorised"
        cat_stats.setdefault(cat, {"count": 0, "views": [], "retention": []})
        cat_stats[cat]["count"] += 1
        cat_stats[cat]["views"].append(r.get("views", 0))
        if r.get("retention_ratio") is not None:
            cat_stats[cat]["retention"].append(r["retention_ratio"])

    category_breakdown = sorted(
        [
            {
                "category":    cat,
                "count":       stats["count"],
                "avg_views":   round(_avg(stats["views"])),
                "avg_retention": round(_avg(stats["retention"]) * 100, 1),
                "share":       round(stats["count"] / len(summary_reels) * 100),
            }
            for cat, stats in cat_stats.items()
        ],
        key=lambda x: x["avg_views"],
        reverse=True,
    )

    # ── Best hook type ────────────────────────────────────────────────────
    hook_stats: dict[str, list] = {}
    for r in summary_reels:
        ht = r.get("hook_type") or "Unknown"
        hook_stats.setdefault(ht, []).append(r.get("views", 0))
    best_hook_type = max(hook_stats, key=lambda h: _avg(hook_stats[h])) if hook_stats else None

    # ── Month label ───────────────────────────────────────────────────────
    month_label = f"{month_name[target_month]} {target_year}"
    compare_label = f"{month_name[prev_month]} {prev_year}" if compare_reels else "Prior average"

    return {
        "has_data":          True,
        "use_all_time":      use_all_time,
        "month_label":       month_label,
        "compare_label":     compare_label,
        "reel_count":        len(summary_reels),
        "total_views":       int(total_views),
        "total_saves":       int(total_saves),
        "total_likes":       int(total_likes),
        "avg_views":         round(avg_views),
        "avg_retention":     round(avg_retention * 100, 1),
        "avg_engagement":    round(avg_engagement * 100, 2),
        "avg_hook":          round(avg_hook, 1),
        "avg_save_rate":     round(avg_save_rate * 100, 2),
        "growth_score":      growth_score,
        "score_label":       score_label,
        "score_colour":      score_colour,
        "score_components": {
            "views":      s_views,
            "retention":  s_ret,
            "engagement": s_eng,
            "save_rate":  s_save,
        },
        "view_change":       round(view_change, 1) if view_change is not None else None,
        "ret_change":        round(ret_change,  1) if ret_change  is not None else None,
        "eng_change":        round(eng_change,  1) if eng_change  is not None else None,
        "save_change":       round(save_change, 1) if save_change is not None else None,
        "most_improved":     most_improved,
        "most_improved_val": round(most_improved_val, 1) if most_improved_val is not None else None,
        "best_reel":         best_reel,
        "best_hook_type":    best_hook_type,
        "category_breakdown": category_breakdown,
        "available_months":  _available_months(reels),
        "target_year":       target_year,
        "target_month":      target_month,
    }


def _available_months(reels: list[dict]) -> list[tuple[int, int]]:
    """Return sorted list of (year, month) tuples that have at least 1 reel."""
    seen = set()
    for r in reels:
        dt = _parse_dt(r)
        if dt:
            seen.add((dt.year, dt.month))
    return sorted(seen, reverse=True)
