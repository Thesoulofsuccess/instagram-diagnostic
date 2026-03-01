"""
patterns.py — Phase 3: Pattern Recognition
Analyses a user's saved reels and surfaces personal benchmarks + AI insights.
Requires at least MIN_REELS reels to generate meaningful patterns.
"""

from __future__ import annotations

import os
from typing import Optional

MIN_REELS = 5  # minimum reels needed before patterns are shown


# ---------------------------------------------------------------------------
# Core maths helpers
# ---------------------------------------------------------------------------

def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct_change(new: float, baseline: float) -> float:
    """Return percentage change vs baseline (positive = better)."""
    if baseline == 0:
        return 0.0
    return ((new - baseline) / baseline) * 100


# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------

def compute_patterns(reels: list[dict]) -> dict:
    """
    Takes a list of raw reel dicts from Supabase and returns a structured
    patterns object ready for the UI to render.
    """
    if not reels or len(reels) < MIN_REELS:
        return {"enough_data": False, "count": len(reels) if reels else 0}

    # --- Personal benchmarks ---
    all_retention   = [r["retention_ratio"]  for r in reels if r.get("retention_ratio")  is not None]
    all_engagement  = [r["engagement_rate"]  for r in reels if r.get("engagement_rate")  is not None]
    all_hook        = [r["hook_score"]        for r in reels if r.get("hook_score")        is not None]
    all_save_rate   = [r["save_rate"]         for r in reels if r.get("save_rate")         is not None]
    all_views       = [r["views"]             for r in reels if r.get("views")             is not None]

    avg_retention  = _avg(all_retention)
    avg_engagement = _avg(all_engagement)
    avg_hook       = _avg(all_hook)
    avg_save_rate  = _avg(all_save_rate)
    avg_views      = _avg(all_views)

    # --- Top and bottom 20 % performers by views ---
    sorted_by_views = sorted(reels, key=lambda r: r.get("views", 0), reverse=True)
    top_n = max(1, len(sorted_by_views) // 5)
    top_performers    = sorted_by_views[:top_n]
    bottom_performers = sorted_by_views[-top_n:]

    # --- Content category breakdown ---
    category_stats: dict[str, dict] = {}
    for r in reels:
        cat = r.get("category") or "Uncategorised"
        if cat not in category_stats:
            category_stats[cat] = {"count": 0, "views": [], "saves": [], "retention": []}
        category_stats[cat]["count"] += 1
        if r.get("views") is not None:
            category_stats[cat]["views"].append(r["views"])
        if r.get("saves") is not None:
            category_stats[cat]["saves"].append(r["saves"])
        if r.get("retention_ratio") is not None:
            category_stats[cat]["retention"].append(r["retention_ratio"])

    category_summary = []
    for cat, stats in category_stats.items():
        category_summary.append({
            "category": cat,
            "count": stats["count"],
            "avg_views": _avg(stats["views"]),
            "avg_saves": _avg(stats["saves"]),
            "avg_retention": _avg(stats["retention"]),
        })
    category_summary.sort(key=lambda x: x["avg_views"], reverse=True)

    # --- Hook type breakdown ---
    hook_stats: dict[str, dict] = {}
    for r in reels:
        ht = r.get("hook_type") or "Unknown"
        if ht not in hook_stats:
            hook_stats[ht] = {"count": 0, "hook_scores": [], "retention": []}
        hook_stats[ht]["count"] += 1
        if r.get("hook_score") is not None:
            hook_stats[ht]["hook_scores"].append(r["hook_score"])
        if r.get("retention_ratio") is not None:
            hook_stats[ht]["retention"].append(r["retention_ratio"])

    hook_summary = []
    for ht, stats in hook_stats.items():
        hook_summary.append({
            "hook_type": ht,
            "count": stats["count"],
            "avg_hook_score": _avg(stats["hook_scores"]),
            "avg_retention": _avg(stats["retention"]),
        })
    hook_summary.sort(key=lambda x: x["avg_hook_score"], reverse=True)

    # --- Recent trend (last 5 vs everything before) ---
    trend = {}
    if len(reels) >= 10:
        recent = reels[:5]
        older  = reels[5:]
        recent_views = _avg([r.get("views", 0) for r in recent])
        older_views  = _avg([r.get("views", 0) for r in older])
        trend = {
            "recent_avg_views": recent_views,
            "older_avg_views":  older_views,
            "change_pct":       _pct_change(recent_views, older_views),
        }

    # --- Underperformers (below 60 % of personal avg views) ---
    threshold = avg_views * 0.6
    underperformers = [r for r in reels if r.get("views", 0) < threshold]

    return {
        "enough_data": True,
        "count": len(reels),
        "benchmarks": {
            "avg_retention":  round(avg_retention,  3),
            "avg_engagement": round(avg_engagement, 3),
            "avg_hook":       round(avg_hook,        1),
            "avg_save_rate":  round(avg_save_rate,  3),
            "avg_views":      round(avg_views,       0),
        },
        "top_performers":    top_performers[:3],
        "bottom_performers": bottom_performers[:3],
        "category_summary":  category_summary,
        "hook_summary":      hook_summary,
        "trend":             trend,
        "underperformers":   underperformers[:5],
    }


# ---------------------------------------------------------------------------
# AI insight generator
# ---------------------------------------------------------------------------

def _build_patterns_prompt(patterns: dict) -> str:
    b  = patterns["benchmarks"]
    cs = patterns["category_summary"]
    hs = patterns["hook_summary"]
    tp = patterns["top_performers"]
    up = patterns["underperformers"]
    tr = patterns.get("trend", {})

    top_titles = ", ".join(
        f'"{r.get("caption","untitled")[:60]}" ({r.get("views",0):,} views)'
        for r in tp
    ) or "none"

    under_titles = ", ".join(
        f'"{r.get("caption","untitled")[:60]}" ({r.get("views",0):,} views)'
        for r in up
    ) or "none"

    top_cat  = cs[0]["category"] if cs else "N/A"
    top_hook = hs[0]["hook_type"] if hs else "N/A"

    trend_line = ""
    if tr:
        direction = "up" if tr["change_pct"] > 0 else "down"
        trend_line = (
            f"Recent trend: last 5 reels average {tr['recent_avg_views']:,.0f} views "
            f"vs {tr['older_avg_views']:,.0f} before — {direction} "
            f"{abs(tr['change_pct']):.0f}%."
        )

    prompt = f"""You are a plain-talking Instagram growth coach for a solo creator with {patterns['count']} reels saved.
Analyse their personal data below and return TWO sections EXACTLY as shown — no extra text, no headings, no markdown.

Personal benchmarks (their own averages — NOT industry averages):
- Average views: {b['avg_views']:,.0f}
- Average retention: {b['avg_retention']*100:.1f}%
- Average engagement rate: {b['avg_engagement']*100:.2f}%
- Average hook score: {b['avg_hook']:.1f}/100
- Average save rate: {b['avg_save_rate']*100:.2f}%

Top content category by avg views: {top_cat}
Best hook type by avg hook score: {top_hook}
Top reels: {top_titles}
Underperforming reels: {under_titles}
{trend_line}

====INSIGHTS====
Write 4–5 bullet points about what the data shows. Each bullet is 1–2 sentences. Start each with "• ".
Talk directly to the creator as "you". Be specific — use their actual numbers. No jargon. No generic advice.

====ROADMAP====
Write exactly 3 priority action items the creator should do RIGHT NOW to improve reach.
Use this exact format for each item — nothing else:

[HIGH] Title of action
One or two sentences describing exactly what to do. Reference their actual data.

[MEDIUM] Title of action
One or two sentences describing exactly what to do. Reference their actual data.

[LOW] Title of action
One or two sentences describing exactly what to do. Reference their actual data.

Priority levels: HIGH = biggest quick win, MEDIUM = important but slower return, LOW = good habit to build.
Each action must be specific to this creator's data — never generic."""

    return prompt


def _parse_roadmap(roadmap_text: str) -> list[dict]:
    """Parse the [HIGH/MEDIUM/LOW] roadmap format into a list of dicts."""
    items = []
    current = None
    for line in roadmap_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        for level in ("HIGH", "MEDIUM", "LOW"):
            tag = f"[{level}]"
            if line.startswith(tag):
                if current:
                    items.append(current)
                title = line[len(tag):].strip()
                current = {"level": level, "title": title, "desc": ""}
                break
        else:
            if current is not None:
                sep = " " if current["desc"] else ""
                current["desc"] += sep + line
    if current:
        items.append(current)
    return items


def generate_ai_content(patterns: dict) -> tuple[Optional[str], Optional[list], Optional[str]]:
    """
    Single OpenAI call returning (insights_text, roadmap_items, error).
    roadmap_items is a list of dicts: [{level, title, desc}, ...]
    """
    if not patterns.get("enough_data"):
        return None, None, "Not enough data."
    try:
        from openai import OpenAI
        try:
            import streamlit as st
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key:
            return None, None, "OpenAI API key not set."

        client = OpenAI(api_key=api_key)
        prompt = _build_patterns_prompt(patterns)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()

        # Split on the section markers
        insights_text = ""
        roadmap_text  = ""
        if "====ROADMAP====" in text:
            parts = text.split("====ROADMAP====", 1)
            insights_raw = parts[0]
            roadmap_text = parts[1].strip()
            # Strip the ====INSIGHTS==== header if present
            insights_text = insights_raw.replace("====INSIGHTS====", "").strip()
        else:
            insights_text = text

        roadmap_items = _parse_roadmap(roadmap_text) if roadmap_text else []
        return insights_text, roadmap_items, None

    except Exception as e:
        return None, None, str(e)


# Keep old name as alias so nothing else breaks
def generate_pattern_insights(patterns: dict) -> tuple[Optional[str], Optional[str]]:
    insights, _, error = generate_ai_content(patterns)
    return insights, error
