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
    # Clamp all interaction counts — negative values are invalid inputs
    likes    = max(0, likes)
    comments = max(0, comments)
    shares   = max(0, shares)
    saves    = max(0, saves)
    total_interactions = likes + comments + shares + saves
    return round(total_interactions / views, 4)


def score_engagement(engagement_rate, follower_count,
                     views=0, likes=0, comments=0, shares=0, saves=0):
    # Clamp raw counts so per-100 breakdown can never go negative
    likes    = max(0, likes)
    comments = max(0, comments)
    shares   = max(0, shares)
    saves    = max(0, saves)
    engagement_rate = max(0.0, engagement_rate)

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

    # ── Per-100-viewer breakdown ───────────────────────────────────────────
    if views > 0:
        per100 = {
            "likes":    round(likes    / views * 100, 1),
            "comments": round(comments / views * 100, 1),
            "shares":   round(shares   / views * 100, 1),
            "saves":    round(saves    / views * 100, 1),
            "total":    round(engagement_rate * 100, 1),
        }
    else:
        per100 = {"likes": 0.0, "comments": 0.0, "shares": 0.0, "saves": 0.0, "total": 0.0}

    # ── Dominant signal + coaching tip ────────────────────────────────────
    save_p    = per100["saves"]
    share_p   = per100["shares"]
    comment_p = per100["comments"]
    like_p    = per100["likes"]

    if save_p >= 3:
        dominant_signal = "saves"
        coaching_tip = (
            "People are bookmarking this — they plan to return and act on it. "
            "Make sure your bio link or offer is front and centre so they can find it easily."
        )
    elif share_p >= 2:
        dominant_signal = "shares"
        coaching_tip = (
            "People are actively spreading this content — you've hit a relatable nerve. "
            "Double down on this topic or format in your next reel."
        )
    elif comment_p >= 1:
        dominant_signal = "comments"
        coaching_tip = (
            "This content is sparking real conversation. "
            "Reply to every comment within the first hour — it signals the algorithm to push your reel to more people."
        )
    elif like_p >= 4:
        dominant_signal = "likes"
        coaching_tip = (
            "You're getting likes but not saves or shares yet. "
            "Try ending your next reel with a specific ask: 'Save this for later' or 'Send this to someone who needs it'."
        )
    else:
        dominant_signal = "none"
        coaching_tip = (
            "No strong action signal yet — that's fixable. "
            "In your next reel, close with one clear ask: 'Save this', 'Share with a friend', or 'Drop a comment below'."
        )

    return {
        "label":           label,
        "explanation":     explanation,
        "rate":            engagement_rate,
        "per100":          per100,
        "dominant_signal": dominant_signal,
        "coaching_tip":    coaching_tip,
    }


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


def score_business_interest(views, saves, shares, comments, follower_count):
    """
    Detects whether saves + shares signal inbound business DM interest.
    Saves = intent to return (purchase/reference).
    Shares = forwarding to others (referral, business vetting).
    High combined = brand scouts, potential partners, clients researching.
    """
    if views == 0:
        return {
            "level": "Unknown",
            "score": 0,
            "dm_likelihood": "Unknown",
            "explanation": "No views data — cannot assess business interest.",
            "signals": [],
            "save_rate": 0,
            "share_rate": 0,
        }

    save_rate = saves / views
    share_rate = shares / views
    comment_rate = comments / views

    signals = []
    score = 0

    # Save signals (purchase intent, reference saving)
    if save_rate >= 0.05:
        score += 4
        signals.append("Very high save rate (" + str(round(save_rate * 100, 1)) + "%) — audience bookmarking for future purchase or reference")
    elif save_rate >= 0.03:
        score += 3
        signals.append("Strong save rate (" + str(round(save_rate * 100, 1)) + "%) — significant portion saving your content for later")
    elif save_rate >= 0.015:
        score += 2
        signals.append("Moderate saves (" + str(round(save_rate * 100, 1)) + "%) — some viewers treating content as reference material")

    # Share signals (referral, business forwarding)
    if share_rate >= 0.03:
        score += 4
        signals.append("Very high share rate (" + str(round(share_rate * 100, 1)) + "%) — content being forwarded to business contacts and teams")
    elif share_rate >= 0.015:
        score += 3
        signals.append("Strong share rate (" + str(round(share_rate * 100, 1)) + "%) — audience actively forwarding to colleagues or clients")
    elif share_rate >= 0.007:
        score += 2
        signals.append("Moderate shares (" + str(round(share_rate * 100, 1)) + "%) — some viewers sharing with their networks")

    # Comment signals (questions = DM trigger)
    if comment_rate >= 0.02:
        score += 2
        signals.append("High comment rate (" + str(round(comment_rate * 100, 1)) + "%) — audience asking questions, a strong precursor to DMs")
    elif comment_rate >= 0.01:
        score += 1
        signals.append("Moderate comments (" + str(round(comment_rate * 100, 1)) + "%) — some interaction beyond passive viewing")

    score = min(score, 10)

    if score >= 7:
        level = "High"
        dm_likelihood = "Very Likely"
        explanation = (
            "Strong business DM signals detected. Your save and share rates indicate brands, agencies, or buyers in your "
            "audience are actively researching you. Ensure your bio has a clear offer, link, or contact email — "
            "these viewers are ready to reach out."
        )
    elif score >= 4:
        level = "Medium"
        dm_likelihood = "Likely"
        explanation = (
            "Moderate business interest detected. Save and share patterns suggest professional audience members are "
            "bookmarking your content. Adding a clear offer or CTA in your bio would convert these passive signals into DMs."
        )
    elif score >= 2:
        level = "Low"
        dm_likelihood = "Possible"
        explanation = (
            "Low business interest signals in this reel. Your saves and shares are below the threshold that typically "
            "triggers inbound brand DMs. Getting your save rate above 3% is the primary lever for attracting business enquiries."
        )
    else:
        level = "None"
        dm_likelihood = "Unlikely"
        explanation = (
            "No significant business interest signals detected. Saves and shares are too low to generate DM activity. "
            "Focus on delivering reference-worthy, high-value content that viewers want to save and send to others."
        )

    return {
        "level": level,
        "score": score,
        "dm_likelihood": dm_likelihood,
        "explanation": explanation,
        "signals": signals,
        "save_rate": round(save_rate, 4),
        "share_rate": round(share_rate, 4),
    }


def segment_audience(views, likes, comments, shares, saves, follower_count, category):
    """
    Categorises a creator's audience into buyer segments based on engagement patterns.

    Segments (from highest to lowest purchase intent):
    - Hot Buyers: high saves + engagement — purchase or booking intent
    - Brand Partners: high shares — brand scouts, agency researchers, referral behaviour
    - Warm Followers: medium engagement, low saves — nurturing phase
    - Passive Viewers: low engagement — awareness only
    """
    if views == 0:
        return []

    save_rate = saves / views
    share_rate = shares / views
    comment_rate = comments / views
    like_rate = likes / views
    engagement_rate = (likes + comments + shares + saves) / views

    hot_pct = 0
    brand_pct = 0
    warm_pct = 0

    # Hot Buyers — save-heavy with engagement
    if save_rate >= 0.03 and engagement_rate >= 0.05:
        hot_pct = min(int(save_rate * 200), 30)
    elif save_rate >= 0.02:
        hot_pct = min(int(save_rate * 150), 20)
    elif save_rate >= 0.01:
        hot_pct = min(int(save_rate * 100), 10)

    # Brand Partners — share-heavy
    if share_rate >= 0.02:
        brand_pct = min(int(share_rate * 200), 20)
    elif share_rate >= 0.01:
        brand_pct = min(int(share_rate * 150), 12)
    elif share_rate >= 0.005:
        brand_pct = min(int(share_rate * 120), 6)

    # Warm Followers — likes + comments but low saves
    if like_rate >= 0.04 and save_rate < 0.02:
        warm_pct = min(int(like_rate * 150), 35)
    elif comment_rate >= 0.01:
        warm_pct = min(int(comment_rate * 300), 25)

    passive_pct = max(0, 100 - hot_pct - brand_pct - warm_pct)

    segments = []

    if hot_pct > 0:
        segments.append({
            "name": "Hot Buyers",
            "icon": "🔥",
            "pct": hot_pct,
            "colour": "#00E5A0",
            "description": f"~{hot_pct}% of viewers show purchase intent — they saved your content, signalling they plan to return and act.",
            "advice": "Put your offer, booking link, or product in your bio and first comment. These viewers are ready to convert — don't make them search.",
        })

    if brand_pct > 0:
        segments.append({
            "name": "Brand Partners",
            "icon": "🤝",
            "pct": brand_pct,
            "colour": "#7DFFCC",
            "description": f"~{brand_pct}% are sharing your content with others — typical of brand scouts, agency researchers, or business owners vetting collaborators.",
            "advice": "Add a 'Collabs & Partnerships' line to your bio. These viewers are most likely to send a business DM or propose a paid deal.",
        })

    if warm_pct > 0:
        segments.append({
            "name": "Warm Followers",
            "icon": "💛",
            "pct": warm_pct,
            "colour": "#FFB020",
            "description": f"~{warm_pct}% are engaged but not yet converting — they like and comment but haven't saved. They're in the consideration phase.",
            "advice": "Nurture with social proof content: testimonials, client results, before/after. They need one more trust signal before converting.",
        })

    if passive_pct > 0:
        segments.append({
            "name": "Passive Viewers",
            "icon": "👀",
            "pct": passive_pct,
            "colour": "#4A4A6A",
            "description": f"~{passive_pct}% watched but took no action. This is expected — not all viewers are buyers.",
            "advice": "Re-hook this group with a CTA in your next reel: 'Save this for later' or 'Send this to someone who needs it'.",
        })

    return segments


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
            follower_count,
            views=views, likes=likes, comments=comments, shares=shares, saves=saves,
        ),
        "hook": score_hook(caption),
        "save_rate": score_save_rate(views, saves),
        "business_interest": score_business_interest(views, saves, shares, comments, follower_count),
        "audience_segments": segment_audience(views, likes, comments, shares, saves, follower_count, category),
    }
    return results
