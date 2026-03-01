"""
email_digest.py  ·  Phase 6: Weekly Email Digest
─────────────────────────────────────────────────
Computes a weekly performance summary from the user's Supabase reel data,
renders a branded HTML email, and sends it via the Resend API.

Requires RESEND_API_KEY in .streamlit/secrets.toml or environment variables.
Free Resend tier: 3,000 emails/month, sends from onboarding@resend.dev.
"""

from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────

def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct_change(new: float, old: float) -> float:
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def _get_resend_key() -> str:
    try:
        import streamlit as st
        return st.secrets.get("RESEND_API_KEY", "")
    except Exception:
        return os.getenv("RESEND_API_KEY", "")


# ─────────────────────────────────────────────────
# DIGEST DATA BUILDER
# ─────────────────────────────────────────────────

def build_digest_data(reels: list[dict], user_email: str) -> dict:
    """
    Compute a structured weekly digest from all user reels.
    Splits reels into 'this week' (last 7 days) vs 'last week' (7–14 days ago).
    Falls back to all-time data if insufficient recent reels.
    """
    now = datetime.now(timezone.utc)
    week_ago     = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    def _parse_dt(r: dict) -> Optional[datetime]:
        raw = r.get("created_at", "")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None

    this_week  = []
    last_week  = []
    older      = []

    for r in reels:
        dt = _parse_dt(r)
        if dt is None:
            older.append(r)
        elif dt >= week_ago:
            this_week.append(r)
        elif dt >= two_weeks_ago:
            last_week.append(r)
        else:
            older.append(r)

    # If fewer than 2 reels this week, use all reels for summary
    use_all = len(this_week) < 2
    summary_reels = reels if use_all else this_week
    compare_reels = (last_week + older) if not use_all else []

    if not summary_reels:
        return {"has_data": False, "user_email": user_email}

    # ── Core metrics ──────────────────────────────
    views_list      = [r.get("views", 0) for r in summary_reels]
    retention_list  = [r.get("retention_ratio", 0) for r in summary_reels if r.get("retention_ratio") is not None]
    engagement_list = [r.get("engagement_rate", 0) for r in summary_reels if r.get("engagement_rate") is not None]
    hook_list       = [r.get("hook_score", 0) for r in summary_reels if r.get("hook_score") is not None]
    saves_list      = [r.get("saves", 0) for r in summary_reels]

    avg_views      = _avg(views_list)
    avg_retention  = _avg(retention_list)
    avg_engagement = _avg(engagement_list)
    avg_hook       = _avg(hook_list)
    total_views    = sum(views_list)
    total_saves    = sum(saves_list)

    # ── Comparison vs prior period ─────────────────
    view_trend     = None
    ret_trend      = None
    if compare_reels:
        prev_views = _avg([r.get("views", 0) for r in compare_reels])
        prev_ret   = _avg([r.get("retention_ratio", 0) for r in compare_reels if r.get("retention_ratio") is not None])
        view_trend = _pct_change(avg_views, prev_views)
        ret_trend  = _pct_change(avg_retention, prev_ret)

    # ── Top & weakest ─────────────────────────────
    sorted_reels = sorted(summary_reels, key=lambda r: r.get("views", 0), reverse=True)
    best_reel    = sorted_reels[0]  if sorted_reels else None
    worst_reel   = sorted_reels[-1] if len(sorted_reels) > 1 else None

    # ── Best category this period ─────────────────
    cat_views: dict[str, list] = {}
    for r in summary_reels:
        cat = r.get("category") or "Uncategorised"
        cat_views.setdefault(cat, []).append(r.get("views", 0))
    best_cat = max(cat_views, key=lambda c: _avg(cat_views[c])) if cat_views else None

    # ── Date range label ──────────────────────────
    if use_all:
        period_label = f"All time · {len(reels)} reels"
    else:
        start = week_ago.strftime("%-d %b") if os.name != "nt" else week_ago.strftime("%d %b").lstrip("0")
        end   = now.strftime("%-d %b") if os.name != "nt" else now.strftime("%d %b").lstrip("0")
        period_label = f"{start} – {end}"

    return {
        "has_data":       True,
        "user_email":     user_email,
        "period_label":   period_label,
        "is_all_time":    use_all,
        "reel_count":     len(summary_reels),
        "total_reels":    len(reels),
        "total_views":    int(total_views),
        "total_saves":    int(total_saves),
        "avg_views":      round(avg_views, 0),
        "avg_retention":  round(avg_retention * 100, 1),
        "avg_engagement": round(avg_engagement * 100, 2),
        "avg_hook":       round(avg_hook, 1),
        "view_trend":     round(view_trend, 1) if view_trend is not None else None,
        "ret_trend":      round(ret_trend, 1)  if ret_trend  is not None else None,
        "best_reel":      best_reel,
        "worst_reel":     worst_reel,
        "best_category":  best_cat,
        "generated_at":   now.strftime("%a %d %b %Y · %H:%M UTC"),
    }


# ─────────────────────────────────────────────────
# HTML EMAIL RENDERER
# ─────────────────────────────────────────────────

def _trend_arrow(val: Optional[float]) -> str:
    if val is None:
        return ""
    if val > 3:
        return f'<span style="color:#00E5A0;font-size:11px;">▲ +{val:.0f}%</span>'
    if val < -3:
        return f'<span style="color:#FF3D71;font-size:11px;">▼ {val:.0f}%</span>'
    return f'<span style="color:#FFB020;font-size:11px;">→ {val:+.0f}%</span>'


def build_digest_html(d: dict) -> str:
    if not d.get("has_data"):
        return "<p>No data available.</p>"

    best  = d.get("best_reel")
    worst = d.get("worst_reel")

    best_caption  = (best.get("caption") or best.get("category") or "Untitled")[:70] if best else "—"
    best_views    = f'{best.get("views", 0):,}' if best else "—"
    best_ret      = f'{(best.get("retention_ratio") or 0)*100:.0f}%' if best else "—"
    best_hook_lbl = best.get("hook_label") or best.get("hook_type") or "—" if best else "—"

    view_arrow = _trend_arrow(d.get("view_trend"))
    ret_arrow  = _trend_arrow(d.get("ret_trend"))

    period_note = (
        f'<p style="margin:0 0 6px;font-size:11px;color:#888;">Showing all {d["total_reels"]} reels logged · '
        f'Log more reels to get a true weekly snapshot.</p>'
        if d.get("is_all_time") else ""
    )

    # Pre-build optional blocks to avoid nested f-string issues
    if worst:
        worst_caption = (worst.get("caption") or worst.get("category") or "Untitled")[:70]
        worst_views   = f'{worst.get("views", 0):,}'
        worst_eng_lbl = worst.get("engagement_label") or "—"
        worst_ret_lbl = worst.get("retention_label") or "—"
        worst_block = (
            '<tr><td style="padding:0 0 20px;">'
            '<table width="100%" cellpadding="0" cellspacing="0"'
            ' style="background:#111;border-left:2px solid #FF3D71;">'
            '<tr><td style="padding:16px 18px;">'
            '<p style="margin:0 0 6px;font-size:10px;color:#FF3D71;'
            'letter-spacing:0.18em;text-transform:uppercase;font-weight:700;">'
            '&#9888; Needs Attention</p>'
            f'<p style="margin:0 0 8px;font-size:14px;color:#E0E0E0;line-height:1.45;">'
            f'"{worst_caption}"</p>'
            f'<p style="margin:0;font-size:11px;color:#555;">'
            f'{worst_views} views &nbsp;&middot;&nbsp; Retention: {worst_ret_lbl}'
            f' &nbsp;&middot;&nbsp; Engagement: {worst_eng_lbl}</p>'
            '</td></tr></table></td></tr>'
        )
    else:
        worst_block = ""

    if d.get("best_category"):
        tip_block = (
            '<tr><td style="padding:0 0 24px;">'
            '<table width="100%" cellpadding="0" cellspacing="0"'
            ' style="background:#0E0E0E;border:1px solid #1F1F1F;border-top:2px solid #FF00FF;">'
            '<tr><td style="padding:18px 18px 16px;">'
            '<p style="margin:0 0 8px;font-size:10px;color:#FF55FF;'
            'letter-spacing:0.18em;text-transform:uppercase;font-weight:700;">'
            '&#128161; Your One Focus This Week</p>'
            f'<p style="margin:0;font-size:13px;color:#AAAAAA;line-height:1.65;">'
            f'Your best-performing category is <strong style="color:#E0E0E0;">'
            f'{d["best_category"]}</strong>. Double down &mdash; create at least one more '
            f'reel in this category and use <strong style="color:#E0E0E0;">Question</strong> '
            f'or <strong style="color:#E0E0E0;">Tutorial / How-To</strong> hooks '
            f'to maximise your {d["avg_retention"]}% retention baseline.</p>'
            '</td></tr></table></td></tr>'
        )
    else:
        tip_block = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reel IQ · Weekly Digest</title>
</head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

  <!-- HEADER -->
  <tr>
    <td style="padding:0 0 28px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;
              background:linear-gradient(90deg,#FF00FF,#FF8C00);
              -webkit-background-clip:text;color:#FF00FF;letter-spacing:-0.5px;">
              REEL<span style="color:#FF8C00;">IQ</span>
            </span>
          </td>
          <td align="right">
            <span style="font-size:11px;color:#444;letter-spacing:0.12em;text-transform:uppercase;">
              Weekly Digest
            </span>
          </td>
        </tr>
      </table>
      <div style="height:1px;background:linear-gradient(90deg,#FF00FF44,#FF8C0022,transparent);margin-top:14px;"></div>
    </td>
  </tr>

  <!-- PERIOD BANNER -->
  <tr>
    <td style="padding:0 0 24px;">
      <p style="margin:0 0 4px;font-size:11px;color:#555;letter-spacing:0.18em;text-transform:uppercase;">Performance Summary</p>
      <p style="margin:0;font-size:20px;font-weight:700;color:#FFFFFF;letter-spacing:-0.03em;">
        {d['period_label']}
      </p>
      {period_note}
    </td>
  </tr>

  <!-- METRIC GRID -->
  <tr>
    <td style="padding:0 0 20px;">
      <table width="100%" cellpadding="0" cellspacing="1" style="background:#222;border-radius:0;">
        <tr>
          <td width="25%" style="background:#111;padding:18px 14px;text-align:center;">
            <div style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:-0.03em;">{d['reel_count']}</div>
            <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.14em;margin-top:4px;">Reels</div>
          </td>
          <td width="25%" style="background:#111;padding:18px 14px;text-align:center;">
            <div style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:-0.03em;">{d['avg_views']:,.0f}</div>
            <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.14em;margin-top:4px;">Avg Views {view_arrow}</div>
          </td>
          <td width="25%" style="background:#111;padding:18px 14px;text-align:center;">
            <div style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:-0.03em;">{d['avg_retention']}%</div>
            <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.14em;margin-top:4px;">Avg Retention {ret_arrow}</div>
          </td>
          <td width="25%" style="background:#111;padding:18px 14px;text-align:center;">
            <div style="font-size:22px;font-weight:700;color:#FFFFFF;letter-spacing:-0.03em;">{d['total_saves']:,}</div>
            <div style="font-size:10px;color:#555;text-transform:uppercase;letter-spacing:0.14em;margin-top:4px;">Total Saves</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- BEST REEL -->
  <tr>
    <td style="padding:0 0 8px;">
      <table width="100%" cellpadding="0" cellspacing="0"
        style="background:#111;border-left:2px solid #00E5A0;">
        <tr>
          <td style="padding:16px 18px;">
            <p style="margin:0 0 6px;font-size:10px;color:#00E5A0;
              letter-spacing:0.18em;text-transform:uppercase;font-weight:700;">
              🏆 Best Reel This Period
            </p>
            <p style="margin:0 0 8px;font-size:14px;color:#E0E0E0;line-height:1.45;">
              "{best_caption}"
            </p>
            <p style="margin:0;font-size:11px;color:#555;">
              {best_views} views &nbsp;·&nbsp; {best_ret} retention &nbsp;·&nbsp; Hook: {best_hook_lbl}
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- WEAKEST REEL -->
  {worst_block}

  <!-- TIP BLOCK -->
  {tip_block}

  <!-- CTA -->
  <tr>
    <td style="padding:0 0 32px;text-align:center;">
      <a href="http://localhost:8501"
        style="display:inline-block;background:linear-gradient(90deg,#FF00FF,#FF8C00);
          color:#FFFFFF;font-size:12px;font-weight:700;letter-spacing:0.16em;
          text-transform:uppercase;padding:12px 32px;text-decoration:none;">
        View Full Dashboard →
      </a>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="border-top:1px solid #1A1A1A;padding-top:20px;">
      <p style="margin:0;font-size:10px;color:#333;text-align:center;line-height:1.8;">
        Reel IQ · AI Content Intelligence<br>
        Generated {d['generated_at']}<br>
        Sent to {d['user_email']}
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ─────────────────────────────────────────────────
# EMAIL SENDER  (Resend)
# ─────────────────────────────────────────────────

def send_digest_email(to_email: str, digest_data: dict) -> tuple[bool, str]:
    """
    Send the weekly digest to the user's email via Resend.
    Returns (True, message_id) on success or (False, error_str) on failure.
    """
    api_key = _get_resend_key()
    if not api_key:
        return False, "RESEND_API_KEY not configured in secrets.toml"

    html = build_digest_html(digest_data)
    period = digest_data.get("period_label", "This Week")

    try:
        import resend
        resend.api_key = api_key
        response = resend.Emails.send({
            "from":    "Reel IQ <onboarding@resend.dev>",
            "to":      [to_email],
            "subject": f"Reel IQ · Your Performance Digest · {period}",
            "html":    html,
        })
        msg_id = response.get("id", "sent")
        return True, msg_id
    except Exception as e:
        return False, str(e)
