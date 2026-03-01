import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from openai import OpenAI
from diagnostic_engine import run_diagnostic


def get_api_key():
    import streamlit as st
    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY")


def generate_ai_report(diagnostic_results):
    inputs = diagnostic_results["inputs"]
    retention = diagnostic_results["retention"]
    engagement = diagnostic_results["engagement"]
    hook = diagnostic_results["hook"]
    save_rate = diagnostic_results["save_rate"]

    prompt = (
        "You are a content performance analyst helping a small business owner "
        "understand why their Instagram Reel underperformed. "
        "Write a clear, specific, plain-language diagnostic report. "
        "No jargon. Every recommendation must reference a specific metric.\n\n"
        "CONTENT DETAILS:\n"
        "Category: " + inputs['category'] + "\n"
        "Follower Count: " + str(inputs['follower_count']) + "\n"
        "Reel Duration: " + str(inputs['reel_duration_seconds']) + " seconds\n"
        "Caption Opening Line: " + hook['first_line'] + "\n\n"
        "DIAGNOSTIC SCORES:\n"
        "Retention: " + retention['label'] + " (" + str(round(retention['ratio'] * 100, 1)) + "% retention ratio)\n"
        "Engagement Rate: " + engagement['label'] + " (" + str(round(engagement['rate'] * 100, 1)) + "%)\n"
        "Hook Strength: " + hook['label'] + " (" + str(hook['score']) + "/10)\n"
        "Save Rate: " + save_rate['label'] + " (" + str(round(save_rate['rate'] * 100, 1)) + "%)\n\n"
        "Write your report in exactly this structure:\n\n"
        "OVERALL DIAGNOSIS\n"
        "2-3 sentences summarising the core problem in plain language.\n\n"
        "WHAT WENT WRONG\n"
        "3 specific findings, each referencing an actual score.\n\n"
        "YOUR TOP 3 ACTIONS\n"
        "3 concrete things to change in the next reel.\n\n"
        "WHAT GOOD LOOKS LIKE\n"
        "1 short paragraph describing what success looks like.\n\n"
        "Keep under 400 words. Plain English only."
    )

    try:
        api_key = get_api_key()
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Instagram content performance analyst helping non-technical small business owners improve their content."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=600,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return "API ERROR: " + str(e)


def generate_pre_score_tips(pre_score_result: dict) -> str:
    """
    Generate 3 specific pre-production AI tips based on the pre-score model output.
    Returns a plain-text string.
    """
    inp   = pre_score_result["inputs"]
    comps = pre_score_result["components"]
    flags = pre_score_result["flags"]

    flags_text = "\n".join(f"- {f}" for f in flags) if flags else "- None identified"

    prompt = (
        "You are an expert Instagram Reels strategist helping a creator optimise a reel "
        "BEFORE they film it. Based on the planned reel details and risk flags below, "
        "give exactly 3 specific, actionable pre-production tips. "
        "Each tip must reference the actual numbers/choices the creator made. "
        "Be direct — no fluff.\n\n"
        "PLANNED REEL DETAILS:\n"
        f"Category: {inp['category']}\n"
        f"Hook Type: {inp['hook_type']}\n"
        f"Planned Duration: {inp['planned_duration_seconds']} seconds\n"
        f"Follower Count: {inp['follower_count']}\n"
        f"Planned Caption Opening: {inp['planned_caption'] or 'Not provided'}\n\n"
        "PRE-SCORE BREAKDOWN:\n"
        f"Overall Pre-Score: {pre_score_result['total']}/100 — {pre_score_result['label']}\n"
        f"Duration Fit: {comps['duration']['score']}/25\n"
        f"Hook Power: {comps['hook']['score']}/25\n"
        f"Category Match: {comps['alignment']['score']}/25\n"
        f"Caption Hook: {comps['caption']['score']}/25\n\n"
        "RISK FLAGS DETECTED:\n"
        f"{flags_text}\n\n"
        "Write exactly 3 tips in this format:\n\n"
        "TIP 1 — [Short bold title]\n"
        "[2-3 sentences. Specific. Reference their actual choice.]\n\n"
        "TIP 2 — [Short bold title]\n"
        "[2-3 sentences. Specific. Reference their actual choice.]\n\n"
        "TIP 3 — [Short bold title]\n"
        "[2-3 sentences. Specific. Reference their actual choice.]\n\n"
        "Under 250 words total. Plain English only."
    )

    try:
        api_key = get_api_key()
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Instagram Reels strategist. "
                        "Give short, specific, actionable advice to creators before they film."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API ERROR: {e}"


def generate_content_brief(
    topic: str,
    goal: str,
    patterns: dict | None,
) -> str:
    """
    Generate a personalised content brief for the creator's next reel.
    If patterns is None or not enough data, falls back to a generic brief.
    """
    # Build personalisation context from real data
    if patterns and patterns.get("enough_data"):
        b  = patterns["benchmarks"]
        cs = patterns.get("category_summary", [])
        hs = patterns.get("hook_summary", [])
        tp = patterns.get("top_performers", [])

        best_category = cs[0]["category"] if cs else "Educational"
        best_hook     = hs[0]["hook_type"] if hs else "Question"
        avg_ret       = b["avg_retention"] * 100
        avg_views     = b["avg_views"]
        avg_save_rate = b["avg_save_rate"] * 100

        # Recommend duration based on retention — if retention is low, go shorter
        if avg_ret < 35:
            rec_duration = "15–25 seconds (your retention drops off quickly — keep it tight)"
        elif avg_ret < 55:
            rec_duration = "25–40 seconds (your retention is solid in this range)"
        else:
            rec_duration = "30–60 seconds (you hold attention well — you can go longer)"

        top_reel_context = ""
        if tp:
            top_reel_context = "Your best-performing reel was: \"" + (tp[0].get("caption") or tp[0].get("category") or "untitled")[:80] + f"\" with {tp[0].get('views', 0):,} views."

        personalisation = f"""CREATOR'S PERSONAL DATA (from {patterns['count']} analysed reels):
- Average views per reel: {avg_views:,.0f}
- Average retention: {avg_ret:.1f}%
- Average save rate: {avg_save_rate:.2f}%
- Best content category (highest avg views): {best_category}
- Best hook type (highest avg hook score): {best_hook}
- Recommended duration: {rec_duration}
- {top_reel_context}

IMPORTANT: This brief MUST use {best_hook} as the hook type and reference the creator's {avg_ret:.1f}% retention baseline when making duration decisions."""

    else:
        best_category = "Educational"
        best_hook     = "Question"
        personalisation = "No personal data available — generate a strong generic brief based on Instagram Reels best practices for 2025."

    prompt = (
        "You are a senior Instagram content strategist creating a production-ready brief "
        "for a creator's next reel. Be direct, specific, and practical.\n\n"
        f"TOPIC: {topic}\n"
        f"GOAL: {goal}\n\n"
        f"{personalisation}\n\n"
        "Write the brief in EXACTLY this structure — no extra commentary:\n\n"
        "━━ FORMAT\n"
        "Duration: [specific seconds range]\n"
        "Hook Type: [type]\n"
        "Category: [category]\n\n"
        "━━ HOOK OPTIONS\n"
        "Write 3 scroll-stopping opening lines for this reel. "
        "Each must be under 12 words and create immediate curiosity or urgency. "
        "Number them 1–3.\n\n"
        "━━ CAPTION STRUCTURE\n"
        "Line 1 (hook): [mirror the best hook option above]\n"
        "Lines 2–4 (value): [what to say in the body]\n"
        f"CTA: [specific call to action aligned with the goal: {goal}]\n\n"
        "━━ CONTENT ANGLE\n"
        "2–3 sentences. What's the specific angle, perspective, or narrative that makes "
        "this reel different from generic content on this topic.\n\n"
        "━━ FILMING NOTES\n"
        "3 short bullet points on how to film/produce this reel for maximum impact. "
        "Reference the hook type and duration.\n\n"
        "Keep the entire brief under 350 words. Plain English only."
    )

    try:
        api_key = get_api_key()
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior Instagram Reels content strategist. "
                        "Write precise, actionable production briefs. "
                        "Every recommendation must be specific and immediately actionable."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.75,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API ERROR: {e}"


