import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ─────────────────────────────────────────
# BENCHMARK DATA
# Source: Hootsuite 2024, Sprout Social 2024
# ─────────────────────────────────────────

BENCHMARKS = {
    "Educational":    {"poor": 0.30, "average": 0.50, "good": 0.70},
    "Inspirational":  {"poor": 0.25, "average": 0.45, "good": 0.65},
    "Transactional":  {"poor": 0.35, "average": 0.55, "good": 0.75},
    "Aesthetic":      {"poor": 0.20, "average": 0.40, "good": 0.60},
    "Entertainment":  {"poor": 0.25, "average": 0.50, "good": 0.70},
}

ENGAGEMENT_BENCHMARKS = {
    "under_1k":  {"poor": 0.03, "average": 0.06, "good": 0.10},
    "1k_5k":     {"poor": 0.02, "average": 0.05, "good": 0.08},
    "5k_10k":    {"poor": 0.015, "average": 0.04, "good": 0.07},
}

HOOK_TRIGGERS = [
    "you", "why", "how", "secret", "mistake", "never", "always",
    "stop", "truth", "warning", "finally", "revealed", "proven",
    "what if", "did you", "most people", "nobody talks"
]


def calculate_retention_ratio(views, watch_time_minutes, reel_duration_seconds):
    if views == 0 or reel_duration_seconds == 0:
        return 0
    total_watch_seconds = watch_time_minutes * 60
    avg_watch_seconds = total_watch_seconds / views
    retention_ratio = avg_watch_seconds / reel_duration_seconds
    return round(min(retention_ratio, 1.0), 3)


def score_retention(retention_ratio, category):
    benchmarks = BENCHMARKS.get(category, BENCHMARKS["Educational"])
    if retention_ratio < benchmarks["poor"]:
        label = "Poor"
        explanation = "Your retention ratio of " + str(round(retention_ratio * 100, 1)) + "% is below the " + category + " category baseline of " + str(int(benchmarks['poor'] * 100)) + "%. Most viewers left almost immediately, suggesting a hook failure in the first 2-3 seconds."
    elif retention_ratio < benchmarks["average"]:
        label = "Below Average"
        explanation = "Your retention ratio of " + str(round(retention_ratio * 100, 1)) + "% is below the " + category + " category average of " + str(int(benchmarks['average'] * 100)) + "%. Your hook pulled some viewers in but failed to sustain attention."
    elif retention_ratio < benchmarks["good"]:
        label = "Average"
        explanation = "Your retention ratio of " + str(round(retention_ratio * 100, 1)) + "% meets the " + category + " category average. Solid performance but room to push into the top tier."
    else:
        label = "Good"
        explanation = "Your retention ratio of " + str(round(retention_ratio * 100, 1)) + "% exceeds the " + category + " category benchmark of " + str(int(benchmarks['good'] * 100)) + "%. Strong viewer retention."
    return {"label": label, "explanation": explanation, "ratio": retention_ratio}


def calculate_engagement_rate(views, likes, comments, shares, saves):
    if views == 0:
        return 0
    total_interactions = likes + comments + shares + saves
    return round(total_interactions / views, 4)


def score_engagement(engagement_rate, follower_count):
    if follower_count < 1000:
        tier = "under_1k"
    elif follower_count < 5000:
        tier = "1k_5k"
    else:
        tier = "5k_10k"
    benchmarks = ENGAGEMENT_BENCHMARKS[tier]
    if engagement_rate < benchmarks["poor"]:
        label = "Poor"
        explanation = "Engagement rate of " + str(round(engagement_rate * 100, 1)) + "% is below average for your follower tier. Your content is not triggering interaction - check your call-to-action and emotional resonance."
    elif engagement_rate < benchmarks["average"]:
        label = "Below Average"
        explanation = "Engagement rate of " + str(round(engagement_rate * 100, 1)) + "% is slightly below average for your follower tier. Small improvements to your CTA could move this significantly."
    elif engagement_rate < benchmarks["good"]:
        label = "Average"
        explanation = "Engagement rate of " + str(round(engagement_rate * 100, 1)) + "% is within the normal range for your follower tier. Solid but not outstanding."
    else:
        label = "Good"
        explanation = "Engagement rate of " + str(round(engagement_rate * 100, 1)) + "% is strong for your follower tier. Your content is resonating well with your audience."
    return {"label": label, "explanation": explanation, "rate": engagement_rate}


def score_hook(caption):
    if not caption or len(caption.strip()) == 0:
        return {
            "score": 0,
            "label": "No Caption",
            "explanation": "No caption was provided. Captions are critical for hook strength and searchability.",
            "first_line": ""
        }
    first_line = caption.strip().split('\n')[0].lower()
    triggers_found = [t for t in HOOK_TRIGGERS if t in first_line]
    score = min(len(triggers_found) * 2.5, 10)
    words = first_line.split()
    if len(words) > 15:
        score = max(score - 2, 0)
        length_note = " Your opening line is too long - aim for under 10 words for maximum scroll-stopping impact."
    else:
        length_note = ""
    if score >= 7:
        label = "Strong"
        explanation = "Your hook contains strong cognitive triggers: " + str(triggers_found) + ". This opening has good scroll-stopping potential." + length_note
    elif score >= 4:
        label = "Moderate"
        explanation = "Your hook has some engaging elements but could be stronger. Triggers found: " + str(triggers_found if triggers_found else "none") + ". Consider opening with a pattern break, bold claim, or direct question." + length_note
    else:
        label = "Weak"
        explanation = "Your hook is weak - no strong cognitive interruption triggers detected. Instagram users scroll at high speed. Your first line needs to create immediate curiosity, urgency, or value. Start with You, a provocative question, or a bold statement." + length_note
    return {
        "score": round(score, 1),
        "label": label,
        "explanation": explanation,
        "first_line": caption.strip().split('\n')[0]
    }


def score_save_rate(views, saves):
    if views == 0:
        return {"rate": 0, "label": "Unknown", "explanation": "No views data available."}
    save_rate = saves / views
    if save_rate >= 0.05:
        label = "Excellent"
        explanation = "Save rate of " + str(round(save_rate * 100, 1)) + "% is exceptional. Your content has high perceived value."
    elif save_rate >= 0.02:
        label = "Good"
        explanation = "Save rate of " + str(round(save_rate * 100, 1)) + "% is above average. Your content delivers enough value that viewers want to return to it."
    elif save_rate >= 0.01:
        label = "Average"
        explanation = "Save rate of " + str(round(save_rate * 100, 1)) + "% is average. Consider adding more actionable takeaways to increase saves."
    else:
        label = "Low"
        explanation = "Save rate of " + str(round(save_rate * 100, 1)) + "% is low. Saves signal deep value to the algorithm. Add tips, lists, or information viewers will want to revisit."
    return {"rate": round(save_rate, 4), "label": label, "explanation": explanation}


def run_diagnostic(views, watch_time_minutes, reel_duration_seconds,
                   likes, comments, shares, saves,
                   caption, category, follower_count):
    retention_ratio = calculate_retention_ratio(views, watch_time_minutes, reel_duration_seconds)
    results = {
        "inputs": {
            "views": views,
            "watch_time_minutes": watch_time_minutes,
            "reel_duration_seconds": reel_duration_seconds,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "saves": saves,
            "caption": caption,
            "category": category,
            "follower_count": follower_count
        },
        "retention": score_retention(retention_ratio, category),
        "engagement": score_engagement(
            calculate_engagement_rate(views, likes, comments, shares, saves),
            follower_count
        ),
        "hook": score_hook(caption),
        "save_rate": score_save_rate(views, saves)
    }
    return results
