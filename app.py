import streamlit as st
import os
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from diagnostic_engine import run_diagnostic
from ai_report import generate_ai_report, generate_pre_score_tips, generate_content_brief
from supabase_client import sign_up, sign_in, reset_password_email, save_reel_analysis, get_user_reels
from patterns import compute_patterns, generate_ai_content, MIN_REELS
from pre_score_engine import run_pre_score
from email_digest import build_digest_data, build_digest_html, send_digest_email
from monthly_card import compute_monthly_card
from competitor import compute_benchmark_report
import theme_engine

# ─────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────
theme_engine.set_page_config()

# ─────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────
_defaults = {
    "authenticated": False,
    "user_id": None,
    "user_email": None,
    "access_token": None,
    "refresh_token": None,
    "save_status": None,
    "save_error_msg": "",
    "patterns_data": None,
    "patterns_insights": None,
    "patterns_roadmap": None,
    "patterns_loaded": False,
    "forgot_pw_mode": False,
    "forgot_pw_sent": False,
    "ps_result": None,
    "ps_tips": None,
    "brief_result": None,
    "brief_topic": "",
    "brief_goal": "",
    "digest_data": None,
    "digest_sent": False,
    "digest_send_msg": "",
    "monthly_data": None,
    "monthly_year": None,
    "monthly_month": None,
    "benchmark_data": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────
CATEGORY_LIST = [
    "Aesthetic", "Beauty", "Business", "Educational",
    "Entertainment", "Fashion", "Food", "Inspirational",
    "Lifestyle", "Music", "Parenting", "Photography",
    "Sport & Fitness", "Transactional", "Travel",
]

CATEGORY_BENCHMARK_MAP = {
    "Aesthetic": "Aesthetic", "Educational": "Educational",
    "Entertainment": "Entertainment", "Inspirational": "Inspirational",
    "Transactional": "Transactional", "Food": "Educational",
    "Travel": "Aesthetic", "Beauty": "Educational",
    "Sport & Fitness": "Educational", "Lifestyle": "Aesthetic",
    "Parenting": "Inspirational", "Business": "Transactional",
    "Music": "Entertainment", "Photography": "Aesthetic",
    "Fashion": "Aesthetic",
}

HOOK_TYPES = [
    "Question", "Bold Statement", "Pattern Interrupt",
    "Story Opening", "How-To / Tutorial", "Shock / Surprise",
    "Before & After", "Controversy", "Other",
]

CSV_FIELD_CANDIDATES = {
    "views": [
        "Views", "Video plays", "Plays", "Reel plays", "Reels plays",
        "Reach", "Impressions", "views", "video_plays", "Accounts reached",
    ],
    "likes": ["Likes", "likes", "Like count", "Reactions"],
    "comments": ["Comments", "comments", "Comment count"],
    "shares": ["Shares", "shares", "Share count"],
    "saves": ["Saves", "saves", "Save count", "Bookmarks"],
    "watch_time_minutes": [
        "Total watch time (minutes)", "Watch time (minutes)",
        "Total watch time", "watch_time_minutes",
    ],
    "reel_duration_seconds": [
        "Duration (seconds)", "Video length (seconds)",
        "Length (seconds)", "Duration", "duration_seconds",
        "Reel duration (seconds)",
    ],
    "caption": [
        "Title", "Description", "Caption", "Post description",
        "description", "title", "Post title",
    ],
    "avg_watch_seconds": [
        "Average watch time per play (seconds)",
        "Average watch time (seconds)",
        "Avg watch time (seconds)",
        "Average watch time per reel play (seconds)",
    ],
    "avg_pct_watched": [
        "Average percentage watched",
        "Average % watched",
        "Avg percentage watched",
    ],
}

FIELD_LABELS = {
    "views": "Views / Plays",
    "likes": "Likes",
    "comments": "Comments",
    "shares": "Shares",
    "saves": "Saves",
    "watch_time_minutes": "Total Watch Time",
    "reel_duration_seconds": "Reel Duration",
    "caption": "Caption / Title",
    "avg_watch_seconds": "Avg Watch Time (sec)",
    "avg_pct_watched": "Avg % Watched",
}


def find_csv_column(df_columns, candidates):
    cols_lower = {c.strip().lower(): c for c in df_columns}
    for candidate in candidates:
        if candidate.strip().lower() in cols_lower:
            return cols_lower[candidate.strip().lower()]
    return None


def build_column_map(df_columns):
    return {
        field: find_csv_column(df_columns, candidates)
        for field, candidates in CSV_FIELD_CANDIDATES.items()
    }


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def row_to_inputs(row, col_map, follower_count, category, hook_type):
    def g(field, default=0.0):
        col = col_map.get(field)
        return safe_float(row[col], default) if col and col in row.index else default

    views = g("views", 0)
    watch_time = g("watch_time_minutes", 0)
    if watch_time == 0:
        avg_sec = g("avg_watch_seconds", 0)
        if avg_sec > 0 and views > 0:
            watch_time = (avg_sec * views) / 60

    duration = g("reel_duration_seconds", 15)
    if duration <= 0:
        duration = 15

    cap_col = col_map.get("caption")
    caption = str(row[cap_col]).strip() if cap_col and cap_col in row.index else ""
    if caption.lower() in ("nan", "none", ""):
        caption = ""

    return {
        "views": int(views),
        "watch_time_minutes": round(watch_time, 4),
        "reel_duration_seconds": int(duration),
        "likes": int(g("likes", 0)),
        "comments": int(g("comments", 0)),
        "shares": int(g("shares", 0)),
        "saves": int(g("saves", 0)),
        "caption": caption,
        "category": category,
        "hook_type": hook_type,
        "follower_count": int(follower_count),
    }


# ─────────────────────────────────────────────────
# CSS  ·  Sharp / Technical / Premium
# ─────────────────────────────────────────────────
def inject_css():
    # ── Foundation design system (fonts, tokens, base components) ──────────
    theme_engine.inject_design_system()
    # ── Feature-specific CSS (tab UIs, phase components) ───────────────────
    st.markdown("""
<style>
/* ── Feature CSS only — base handled by theme_engine.inject_design_system() ── */

/* ══════════════════════════════════════
   CSV IMPORT
══════════════════════════════════════ */
.csv-info-card {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 2px solid #833AB4;
    padding: 1.4rem 1.6rem; margin-bottom: 1.6rem;
}
.csv-info-title {
    font-family: 'Inter', sans-serif; font-size: 0.85rem; font-weight: 700;
    color: #FFFFFF; margin-bottom: 0.42rem; letter-spacing: 0.02em;
}
.csv-info-text { font-size: 0.80rem; color: rgba(255,255,255,0.38); line-height: 1.68; }
.csv-info-steps { margin: 0.9rem 0 0; padding-left: 1.3rem; }
.csv-info-steps li { font-size: 0.78rem; color: rgba(255,255,255,0.38); margin-bottom: 0.38rem; line-height: 1.55; }
.csv-info-steps li span { color: rgba(150,80,210,0.85); font-weight: 600; }

.col-map-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 1px; margin: 0.9rem 0 1.4rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.06);
}
.col-map-row {
    display: flex; align-items: center; gap: 0.65rem;
    background: #111111; padding: 0.6rem 0.9rem;
}
.col-map-icon { font-size: 0.78rem; flex-shrink: 0; }
.col-map-field { color: rgba(255,255,255,0.28); font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; font-size: 0.58rem; flex: 1; }
.col-map-value { color: #FFFFFF; font-weight: 500; font-size: 0.75rem; text-align: right; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-map-missing .col-map-value { color: rgba(255,255,255,0.22); font-style: italic; }

.import-summary-card {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-top: 2px solid;
    border-image: linear-gradient(90deg, #833AB4, #FCB045) 1;
    padding: 1.6rem; margin-top: 1.4rem;
}
.import-summary-title {
    font-family: 'Inter', sans-serif; font-size: 0.80rem; font-weight: 700;
    color: #FFFFFF; margin-bottom: 1.1rem; padding-bottom: 0.9rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    letter-spacing: 0.10em; text-transform: uppercase;
}
.import-stats {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1px; margin-bottom: 1.1rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.06);
}
.import-stat { text-align: center; background: #111111; padding: 1.1rem 0.5rem; }
.import-stat-num { font-family: 'Inter', sans-serif; font-size: 1.9rem; font-weight: 800; line-height: 1; }
.import-stat-label { font-size: 0.56rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: rgba(255,255,255,0.22); margin-top: 0.38rem; font-family: 'Inter', sans-serif; }
.import-stat.success .import-stat-num { color: #00E5A0; }
.import-stat.skipped .import-stat-num { color: #FFB020; }
.import-stat.failed  .import-stat-num { color: #FF3D71; }
.import-note { font-size: 0.78rem; color: rgba(255,255,255,0.35); line-height: 1.68; }
.import-note p { margin: 0 0 0.45rem; }
.import-note p:last-child { margin-bottom: 0; }

/* ══════════════════════════════════════
   FILE UPLOADER
══════════════════════════════════════ */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.018) !important;
    border: 1px dashed rgba(131,58,180,0.22) !important;
    border-radius: 0px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: rgba(131,58,180,0.42) !important; }

/* ══════════════════════════════════════
   DATAFRAME
══════════════════════════════════════ */
[data-testid="stDataFrame"] { border-radius: 0px !important; overflow: hidden; }

/* ══════════════════════════════════════
   PROGRESS BAR
══════════════════════════════════════ */
.stProgress > div > div {
    background: linear-gradient(90deg, #833AB4, #FCB045) !important;
    border-radius: 0px !important;
}
.stProgress > div { background: rgba(255,255,255,0.05) !important; border-radius: 0px !important; }

/* ══════════════════════════════════════
   MISC OVERRIDES
══════════════════════════════════════ */
div[data-testid="stForm"] { background: transparent !important; border: none !important; padding: 0 !important; }
.stAlert { border-radius: 0px !important; }
.stSuccess { background: rgba(0,229,160,0.05) !important; border: 1px solid rgba(0,229,160,0.15) !important; color: #00E5A0 !important; border-radius: 0px !important; }
.stError   { background: rgba(255,61,113,0.05) !important; border: 1px solid rgba(255,61,113,0.15) !important; border-radius: 0px !important; }
hr { border-color: rgba(255,255,255,0.06) !important; margin: 2rem 0 !important; }
.stNumberInput button { background: rgba(255,255,255,0.03) !important; border-color: rgba(255,255,255,0.10) !important; color: rgba(255,255,255,0.35) !important; }

/* ══════════════════════════════════════
   PATTERNS TAB
══════════════════════════════════════ */
.patterns-hero { text-align: center; padding: 1.25rem 0 1rem; }
.patterns-hero h2 {
    font-family: 'Inter', sans-serif; font-size: 1.6rem; font-weight: 800;
    background: linear-gradient(90deg, #833AB4, #FCB045);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 0.4rem;
}
.patterns-hero p { color: rgba(255,255,255,0.28); font-size: 0.85rem; margin: 0; }

.patterns-gate {
    text-align: center; padding: 3.5rem 2rem;
    background: #111111; border: 1px solid rgba(255,255,255,0.07);
    margin: 1.5rem 0;
}
.patterns-gate h3 {
    font-family: 'Inter', sans-serif; font-size: 1.2rem; font-weight: 700;
    color: #FFFFFF; margin: 0 0 0.6rem;
}
.patterns-gate p { color: rgba(255,255,255,0.32); font-size: 0.875rem; line-height: 1.68; margin: 0; }
.gate-count {
    font-size: 3rem; font-weight: 800; font-family: 'Inter', sans-serif;
    background: linear-gradient(90deg, #833AB4, #FCB045);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    display: block; margin-bottom: 0.85rem; line-height: 1;
}

/* Flush bench grid */
.bench-grid {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 1px; margin: 1.4rem 0;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.07);
}
@media (min-width: 580px) { .bench-grid { grid-template-columns: repeat(4, 1fr); } }
.bench-card {
    background: #111111; padding: 1.35rem 1rem; text-align: center;
    position: relative; overflow: hidden;
    transition: background 0.18s;
}
.bench-card:hover { background: #111111; }
.bench-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.bench-views::before  { background: linear-gradient(90deg, #6600CC, #BB00FF); }
.bench-ret::before    { background: linear-gradient(90deg, #0055BB, #0099FF); }
.bench-eng::before    { background: linear-gradient(90deg, #AA0044, #FF2277); }
.bench-save::before   { background: linear-gradient(90deg, #008855, #00E5A0); }
.bench-hook::before   { background: linear-gradient(90deg, #AA6600, #FFB020); }

.bench-val {
    font-family: 'Inter', sans-serif; font-size: 1.65rem; font-weight: 800; line-height: 1;
}
.bench-views .bench-val { color: #BB00FF; }
.bench-ret .bench-val   { color: #0099FF; }
.bench-eng .bench-val   { color: #FF2277; }
.bench-save .bench-val  { color: #00E5A0; }
.bench-hook .bench-val  { color: #FFB020; }

.bench-label {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: rgba(255,255,255,0.22);
    margin-top: 0.45rem; font-family: 'Inter', sans-serif;
}

.insights-box {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 2px solid #833AB4;
    padding: 1.65rem 1.8rem; margin: 1.4rem 0;
}
.insights-box p { color: rgba(255,255,255,0.52); font-size: 0.875rem; line-height: 1.82; margin: 0; white-space: pre-wrap; }

.breakdown-table { width: 100%; border-collapse: collapse; margin: 0.9rem 0; }
.breakdown-table th {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: rgba(255,255,255,0.22);
    padding: 0 0 0.8rem; text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-family: 'Inter', sans-serif;
}
.breakdown-table td {
    padding: 0.7rem 0; font-size: 0.84rem; color: rgba(255,255,255,0.52);
    border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: middle;
    font-family: 'Inter', sans-serif;
}
.breakdown-table td:not(:first-child) { text-align: right; color: rgba(255,255,255,0.32); }
.breakdown-table tr:last-child td { border-bottom: none; }
.breakdown-table tr:hover td { background: rgba(255,255,255,0.02); color: rgba(255,255,255,0.70); }
.breakdown-table tr:hover td:not(:first-child) { color: rgba(255,255,255,0.45); }

.top-reel-card {
    background: #111111; border: 1px solid rgba(255,255,255,0.07);
    border-left: 2px solid #00E5A0;
    padding: 1rem 1.25rem; margin-bottom: 2px;
    transition: background 0.15s;
}
.top-reel-card:hover { background: #111111; }
.top-reel-card .reel-caption {
    font-size: 0.875rem; color: rgba(255,255,255,0.70); font-weight: 500;
    margin-bottom: 0.42rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.top-reel-card .reel-stats { font-size: 0.72rem; color: rgba(255,255,255,0.26); }
.reel-stat-pill {
    display: inline-block; background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 0; padding: 0.18rem 0.6rem; margin-right: 0.4rem;
}
.under-card { border-left-color: #FF3D71 !important; }

.trend-badge {
    display: inline-flex; align-items: center; gap: 0.45rem;
    padding: 0.4rem 1rem; border-radius: 0;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    font-family: 'Inter', sans-serif;
}
.trend-up   { background: rgba(0,229,160,0.08);  color: #00E5A0; border: 1px solid rgba(0,229,160,0.20); }
.trend-down { background: rgba(255,61,113,0.08); color: #FF3D71; border: 1px solid rgba(255,61,113,0.20); }
.trend-flat { background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.35); border: 1px solid rgba(255,255,255,0.08); }

/* ══════════════════════════════════════
   PRIORITY ROADMAP
══════════════════════════════════════ */
.roadmap-card {
    background: #111111; border: 1px solid rgba(255,255,255,0.07);
    padding: 1.1rem 1.3rem; margin-bottom: 2px;
    display: flex; gap: 1.1rem; align-items: flex-start;
    transition: background 0.15s;
}
.roadmap-card:hover { background: #111111; }
.roadmap-HIGH   { border-left: 2px solid #FF3D71; }
.roadmap-MEDIUM { border-left: 2px solid #FFB020; }
.roadmap-LOW    { border-left: 2px solid #00E5A0; }
.priority-badge {
    display: inline-block; padding: 0.22rem 0.82rem; border-radius: 0;
    font-size: 0.52rem; font-weight: 800;
    letter-spacing: 0.18em; text-transform: uppercase;
    white-space: nowrap; flex-shrink: 0; margin-top: 0.2rem;
    font-family: 'Inter', sans-serif;
}
.priority-HIGH   { background: rgba(255,61,113,0.10);  color: #FF3D71; border: 1px solid rgba(255,61,113,0.22); }
.priority-MEDIUM { background: rgba(255,176,32,0.10);  color: #FFB020; border: 1px solid rgba(255,176,32,0.22); }
.priority-LOW    { background: rgba(0,229,160,0.08);   color: #00E5A0; border: 1px solid rgba(0,229,160,0.20); }
.roadmap-body { flex: 1; min-width: 0; }
.roadmap-title { font-size: 0.875rem; font-weight: 600; color: rgba(255,255,255,0.82); margin-bottom: 0.35rem; line-height: 1.35; font-family: 'Inter', sans-serif; }
.roadmap-desc  { font-size: 0.80rem; color: rgba(255,255,255,0.32); line-height: 1.72; font-family: 'Inter', sans-serif; }

/* ══════════════════════════════════════
   PRE-SCORE TAB  ·  Phase 4
══════════════════════════════════════ */
.prescore-hero {
    text-align: center; padding: 0.5rem 0 1.75rem;
}
.prescore-hero-title {
    font-family: 'Inter', sans-serif; font-size: 1.55rem; font-weight: 800;
    color: #FFFFFF; letter-spacing: -0.02em; margin-bottom: 0.4rem; line-height: 1.1;
}
.prescore-hero-sub {
    font-size: 0.82rem; color: rgba(255,255,255,0.35); line-height: 1.65;
}

/* Big circular score ring */
.prescore-ring-wrap {
    display: flex; flex-direction: column; align-items: center;
    padding: 1.8rem 1rem 1.4rem;
}
.prescore-ring {
    position: relative; width: 148px; height: 148px; margin-bottom: 1.1rem;
}
.prescore-ring svg { transform: rotate(-90deg); }
.prescore-ring-bg   { fill: none; stroke: rgba(255,255,255,0.06); stroke-width: 8; }
.prescore-ring-fill { fill: none; stroke-width: 8; stroke-linecap: butt;
                      transition: stroke-dashoffset 0.9s cubic-bezier(.4,0,.2,1); }
.prescore-ring-fill.good    { stroke: url(#ringGrad); }
.prescore-ring-fill.average { stroke: #FFB020; }
.prescore-ring-fill.poor    { stroke: #FF3D71; }
.prescore-inner {
    position: absolute; inset: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.prescore-number {
    font-family: 'Inter', sans-serif; font-size: 2.6rem; font-weight: 800;
    line-height: 1; letter-spacing: -0.02em;
}
.prescore-number.good    { color: #00E5A0; }
.prescore-number.average { color: #FFB020; }
.prescore-number.poor    { color: #FF3D71; }
.prescore-label {
    font-size: 0.55rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: rgba(255,255,255,0.28);
    margin-top: 0.2rem;
}
.prescore-verdict {
    font-size: 0.78rem; color: rgba(255,255,255,0.40); text-align: center;
    line-height: 1.6; max-width: 260px;
}

/* Component bar grid */
.prescore-components {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 1px; margin: 1.2rem 0;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.06);
}
.prescore-comp {
    background: #111111; padding: 1.1rem 1.2rem;
    display: flex; flex-direction: column; gap: 0.55rem;
}
.prescore-comp-top {
    display: flex; justify-content: space-between; align-items: baseline;
}
.prescore-comp-name {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: rgba(255,255,255,0.30);
    font-family: 'Inter', sans-serif;
}
.prescore-comp-val {
    font-family: 'Inter', sans-serif; font-size: 1.05rem; font-weight: 800;
    color: #FFFFFF; line-height: 1;
}
.prescore-bar-track {
    height: 3px; background: rgba(255,255,255,0.07); border-radius: 0;
}
.prescore-bar-fill {
    height: 3px; border-radius: 0;
    background: linear-gradient(90deg, #833AB4, #FCB045);
    transition: width 0.6s ease;
}

/* Risk flags */
.risk-flag {
    display: flex; gap: 0.75rem; align-items: flex-start;
    background: rgba(255,61,113,0.04);
    border: 1px solid rgba(255,61,113,0.14);
    border-left: 2px solid #FF3D71;
    padding: 0.85rem 1rem; margin-bottom: 2px;
}
.risk-icon { font-size: 0.75rem; flex-shrink: 0; margin-top: 0.05rem; color: #FF3D71; }
.risk-text { font-size: 0.80rem; color: rgba(255,255,255,0.45); line-height: 1.65; }

/* AI tips block */
.prescore-tips {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-top: 2px solid;
    border-image: linear-gradient(90deg, #833AB4, #FCB045) 1;
    padding: 1.6rem 1.8rem; margin-top: 1.2rem;
}
.prescore-tips-header {
    display: flex; align-items: center; gap: 0.8rem;
    margin-bottom: 1.2rem; padding-bottom: 0.9rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.prescore-tips-dot {
    width: 8px; height: 8px; flex-shrink: 0;
    background: linear-gradient(90deg, #833AB4, #FCB045);
    border-radius: 0; box-shadow: 0 0 10px rgba(131,58,180,0.50);
}
.prescore-tips-title {
    font-family: 'Inter', sans-serif; font-size: 0.85rem;
    font-weight: 700; color: #FFFFFF; letter-spacing: 0.02em;
}
.prescore-tips-sub { font-size: 0.66rem; color: rgba(255,255,255,0.26); margin-top: 0.1rem; }
.prescore-tips-body {
    font-size: 0.875rem; color: rgba(255,255,255,0.50);
    line-height: 1.95; white-space: pre-wrap;
}

/* ══════════════════════════════════════
   CONTENT BRIEF  ·  Phase 5
══════════════════════════════════════ */
.brief-hero {
    text-align: center; padding: 0.5rem 0 1.75rem;
}
.brief-hero-title {
    font-family: 'Inter', sans-serif; font-size: 1.55rem; font-weight: 800;
    color: #FFFFFF; letter-spacing: -0.02em; margin-bottom: 0.4rem; line-height: 1.1;
}
.brief-hero-sub {
    font-size: 0.82rem; color: rgba(255,255,255,0.35); line-height: 1.65;
}

/* Personalisation chip — shown when patterns data is available */
.brief-data-chip {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: rgba(0,229,160,0.06); border: 1px solid rgba(0,229,160,0.18);
    color: #00E5A0; font-size: 0.60rem; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    padding: 0.3rem 0.9rem; border-radius: 0; margin-bottom: 1.4rem;
}
.brief-data-chip.generic {
    background: rgba(255,176,32,0.06); border-color: rgba(255,176,32,0.18);
    color: #FFB020;
}

/* Goal pills */
.brief-goals {
    display: flex; gap: 6px; flex-wrap: wrap; margin-top: 0.55rem;
}

/* The brief output card */
.brief-card {
    background: #0D0D0D;
    border: 1px solid rgba(255,255,255,0.08);
    border-top: 2px solid;
    border-image: linear-gradient(90deg, #833AB4, #FCB045) 1;
    margin-top: 1.35rem;
    overflow: hidden;
}
.brief-card-header {
    display: flex; align-items: center; gap: 0.9rem;
    padding: 1.4rem 1.8rem 1.1rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.brief-card-dot {
    width: 8px; height: 8px; flex-shrink: 0; border-radius: 0;
    background: linear-gradient(90deg, #833AB4, #FCB045);
    box-shadow: 0 0 10px rgba(131,58,180,0.50);
}
.brief-card-title {
    font-family: 'Inter', sans-serif; font-size: 0.85rem;
    font-weight: 700; color: #FFFFFF; letter-spacing: 0.02em;
}
.brief-card-meta {
    font-size: 0.64rem; color: rgba(255,255,255,0.24); margin-top: 0.1rem;
}
.brief-card-topic {
    margin-left: auto; font-size: 0.68rem; font-weight: 600;
    color: rgba(131,58,180,0.70); letter-spacing: 0.06em;
    max-width: 180px; text-align: right;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Section blocks inside brief */
.brief-section {
    padding: 1.15rem 1.8rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.brief-section:last-child { border-bottom: none; }
.brief-section-label {
    font-size: 0.54rem; font-weight: 700; letter-spacing: 0.22em;
    text-transform: uppercase; color: rgba(131,58,180,0.55);
    margin-bottom: 0.7rem; font-family: 'Inter', sans-serif;
}
.brief-section-body {
    font-size: 0.875rem; color: rgba(255,255,255,0.52);
    line-height: 1.85; white-space: pre-wrap;
}
.brief-hook-option {
    background: rgba(255,255,255,0.025);
    border-left: 2px solid rgba(131,58,180,0.30);
    padding: 0.6rem 1rem; margin-bottom: 4px;
    font-size: 0.875rem; color: rgba(255,255,255,0.72);
    font-weight: 500; line-height: 1.55;
}
.brief-format-pills {
    display: flex; flex-wrap: wrap; gap: 6px;
}
.brief-format-pill {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    padding: 0.3rem 0.75rem;
    font-size: 0.70rem; color: rgba(255,255,255,0.55); font-weight: 500;
}
.brief-format-pill span {
    color: #FFFFFF; font-weight: 700;
}

/* ══════════════════════════════════════
   WEEKLY DIGEST  ·  Phase 6
══════════════════════════════════════ */
.digest-hero { text-align: center; padding: 0.5rem 0 1.75rem; }
.digest-hero-title {
    font-family: 'Inter', sans-serif; font-size: 1.55rem; font-weight: 800;
    color: #FFFFFF; letter-spacing: -0.02em; margin-bottom: 0.4rem;
}
.digest-hero-sub { font-size: 0.82rem; color: rgba(255,255,255,0.35); line-height: 1.65; }

.digest-stat-row {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1px; margin: 0.85rem 0;
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.07);
}
@media (max-width:640px) { .digest-stat-row { grid-template-columns: repeat(2,1fr); } }
.digest-stat { background:#111; padding:1.1rem 0.75rem; text-align:center; }
.digest-stat-val {
    font-family:'Inter',sans-serif; font-size:1.55rem; font-weight:800;
    color:#FFFFFF; line-height:1; letter-spacing:-0.02em;
}
.digest-stat-label {
    font-size:0.54rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:rgba(255,255,255,0.22); margin-top:0.35rem;
}
.digest-trend-up   { color:#00E5A0; font-size:0.62rem; font-weight:700; }
.digest-trend-down { color:#FF3D71; font-size:0.62rem; font-weight:700; }
.digest-trend-flat { color:#FFB020; font-size:0.62rem; font-weight:700; }

.digest-reel-card { padding:0.9rem 1rem; margin-bottom:2px; border-left:2px solid transparent; }
.digest-reel-card.best  { background:rgba(0,229,160,0.04); border-color:#00E5A0; }
.digest-reel-card.worst { background:rgba(255,61,113,0.04); border-color:#FF3D71; }
.digest-reel-badge {
    font-size:0.54rem; font-weight:700; letter-spacing:0.16em; text-transform:uppercase; margin-bottom:0.35rem;
}
.digest-reel-card.best  .digest-reel-badge { color:#00E5A0; }
.digest-reel-card.worst .digest-reel-badge { color:#FF3D71; }
.digest-reel-caption { font-size:0.82rem; color:rgba(255,255,255,0.72); font-weight:500; line-height:1.45; margin-bottom:0.3rem; }
.digest-reel-stats  { font-size:0.68rem; color:rgba(255,255,255,0.28); }

.digest-tip {
    background:#111111; border:1px solid rgba(255,255,255,0.06);
    border-top:2px solid #833AB4; padding:1rem 1.2rem; margin-top:0.6rem;
}
.digest-tip-label {
    font-size:0.54rem; font-weight:700; letter-spacing:0.18em;
    text-transform:uppercase; color:rgba(131,58,180,0.65); margin-bottom:0.4rem;
}
.digest-tip-body { font-size:0.82rem; color:rgba(255,255,255,0.42); line-height:1.65; }

.digest-setup-note {
    background:rgba(255,176,32,0.04); border:1px solid rgba(255,176,32,0.14);
    border-left:2px solid #FFB020; padding:0.85rem 1rem; margin-top:0.85rem;
    font-size:0.78rem; color:rgba(255,255,255,0.42); line-height:1.65;
}
.digest-setup-note code {
    background:rgba(255,255,255,0.07); padding:0.1rem 0.4rem;
    font-family:'Courier New',monospace; font-size:0.72rem; color:rgba(255,176,32,0.85);
}

/* ══════════════════════════════════════
   MONTHLY CARD  ·  Phase 7
══════════════════════════════════════ */
.monthly-hero { text-align:center; padding:0.5rem 0 1.75rem; }
.monthly-hero-title {
    font-family:'Inter',sans-serif; font-size:1.55rem; font-weight:800;
    color:#FFFFFF; letter-spacing:-0.02em; margin-bottom:0.4rem;
}
.monthly-hero-sub { font-size:0.82rem; color:rgba(255,255,255,0.35); line-height:1.65; }

/* Month header card */
.month-header {
    background: linear-gradient(135deg, #111 0%, #0D0D0D 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-top: 2px solid;
    border-image: linear-gradient(90deg,#833AB4,#FCB045) 1;
    padding: 1.6rem 1.8rem 1.4rem;
    margin-bottom: 1px;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
}
.month-name {
    font-family:'Inter',sans-serif; font-size:2rem; font-weight:800;
    letter-spacing:-0.02em; line-height:1;
    background:linear-gradient(90deg,#833AB4,#FCB045);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.month-compare-label {
    font-size:0.60rem; color:rgba(255,255,255,0.22); letter-spacing:0.16em;
    text-transform:uppercase; margin-top:0.3rem;
}

/* Growth score ring in monthly card */
.monthly-score-wrap { display:flex; align-items:center; gap:1.4rem; }
.monthly-score-ring { position:relative; width:88px; height:88px; flex-shrink:0; }
.monthly-score-ring svg { display:block; }
.monthly-score-inner {
    position:absolute; inset:0;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
}
.monthly-score-num {
    font-family:'Inter',sans-serif; font-size:1.55rem; font-weight:800; line-height:1;
    letter-spacing:-0.02em;
}
.monthly-score-num.good    { color:#00E5A0; }
.monthly-score-num.average { color:#FFB020; }
.monthly-score-num.poor    { color:#FF3D71; }
.monthly-score-lbl {
    font-size:0.48rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:rgba(255,255,255,0.22); margin-top:0.1rem;
}
.monthly-score-verdict { }
.monthly-score-verdict-label {
    font-family:'Inter',sans-serif; font-size:0.95rem; font-weight:800;
    line-height:1.1; letter-spacing:-0.02em;
}
.monthly-score-verdict-label.good    { color:#00E5A0; }
.monthly-score-verdict-label.average { color:#FFB020; }
.monthly-score-verdict-label.poor    { color:#FF3D71; }
.monthly-score-verdict-sub {
    font-size:0.68rem; color:rgba(255,255,255,0.28); margin-top:0.25rem; line-height:1.5;
}

/* Totals row */
.monthly-totals {
    display:grid; grid-template-columns:repeat(3,1fr);
    gap:1px; background:rgba(255,255,255,0.07);
    border:1px solid rgba(255,255,255,0.07); margin-bottom:1px;
}
.monthly-total { background:#111; padding:1.1rem 0.75rem; text-align:center; }
.monthly-total-val {
    font-family:'Inter',sans-serif; font-size:1.85rem; font-weight:800;
    color:#FFFFFF; line-height:1; letter-spacing:-0.02em;
}
.monthly-total-label {
    font-size:0.54rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:rgba(255,255,255,0.22); margin-top:0.35rem;
}

/* MoM metric row */
.monthly-metrics {
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:1px; background:rgba(255,255,255,0.06);
    border:1px solid rgba(255,255,255,0.06); margin-bottom:1px;
}
@media(max-width:640px) { .monthly-metrics { grid-template-columns:repeat(2,1fr); } }
.monthly-metric { background:#111111; padding:1rem 0.8rem; }
.monthly-metric-label {
    font-size:0.52rem; font-weight:700; letter-spacing:0.16em;
    text-transform:uppercase; color:rgba(255,255,255,0.22); margin-bottom:0.45rem;
}
.monthly-metric-val {
    font-family:'Inter',sans-serif; font-size:1.3rem; font-weight:800;
    color:#FFFFFF; line-height:1; letter-spacing:-0.02em;
}
.monthly-metric-change { font-size:0.64rem; font-weight:700; margin-top:0.28rem; }
.monthly-metric-change.up   { color:#00E5A0; }
.monthly-metric-change.down { color:#FF3D71; }
.monthly-metric-change.flat { color:#FFB020; }

/* Category breakdown bars */
.monthly-cat-row {
    display:flex; align-items:center; gap:0.75rem;
    padding:0.55rem 0; border-bottom:1px solid rgba(255,255,255,0.04);
}
.monthly-cat-row:last-child { border-bottom:none; }
.monthly-cat-name {
    font-size:0.72rem; font-weight:600; color:rgba(255,255,255,0.65);
    min-width:110px; flex-shrink:0;
}
.monthly-cat-bar-track {
    flex:1; height:4px; background:rgba(255,255,255,0.06); border-radius:0;
}
.monthly-cat-bar-fill {
    height:4px; border-radius:0;
    background:linear-gradient(90deg,#833AB4,#FCB045);
    transition:width 0.6s ease;
}
.monthly-cat-views {
    font-size:0.64rem; color:rgba(255,255,255,0.28);
    min-width:70px; text-align:right; flex-shrink:0;
}

/* Best reel highlight */
.monthly-best-reel {
    background:#111111; border:1px solid rgba(255,255,255,0.06);
    border-left:2px solid #00E5A0; padding:1rem 1.2rem; margin-top:1px;
}
.monthly-best-badge {
    font-size:0.54rem; font-weight:700; letter-spacing:0.16em;
    text-transform:uppercase; color:#00E5A0; margin-bottom:0.4rem;
}
.monthly-best-caption {
    font-size:0.875rem; color:rgba(255,255,255,0.72); font-weight:500; line-height:1.45;
    margin-bottom:0.35rem;
}
.monthly-best-stats { font-size:0.68rem; color:rgba(255,255,255,0.28); }

/* Most improved badge */
.monthly-improved {
    display:inline-flex; align-items:center; gap:0.45rem;
    background:rgba(0,229,160,0.06); border:1px solid rgba(0,229,160,0.16);
    padding:0.28rem 0.75rem; margin-bottom:0.6rem;
    font-size:0.62rem; font-weight:700; letter-spacing:0.12em;
    text-transform:uppercase; color:#00E5A0;
}

/* ══════════════════════════════════════
   PHASE 8 — BENCHMARK COMPARISON
══════════════════════════════════════ */
.bench-hero { text-align:center; padding:2.2rem 0 1.6rem; }
.bench-hero-title {
    font-family:'Inter',sans-serif; font-size:1.55rem; font-weight:800;
    background:linear-gradient(90deg,#833AB4 0%,#FCB045 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:0.35rem;
}
.bench-hero-sub { font-size:0.82rem; color:rgba(255,255,255,0.40); max-width:480px; margin:0 auto; }

/* Tier badge */
.bench-tier-badge {
    display:inline-flex; align-items:center; gap:0.4rem;
    background:rgba(131,58,180,0.08); border:1px solid rgba(131,58,180,0.22);
    padding:0.22rem 0.75rem; font-size:0.62rem; font-weight:700;
    letter-spacing:0.12em; text-transform:uppercase; color:#833AB4;
    margin-bottom:1.2rem;
}

/* Score ring */
.bench-score-wrap { display:flex; flex-direction:column; align-items:center; margin:1.4rem 0 0.6rem; }
.bench-score-ring svg { overflow:visible; }
.bench-score-label {
    font-family:'Inter',sans-serif; font-size:1.0rem; font-weight:800;
    margin-top:0.4rem; letter-spacing:0.04em;
}
.bench-score-num {
    font-family:'Inter',sans-serif; font-size:2.2rem; font-weight:800;
    line-height:1;
}

/* 2×2 metric comparison grid */
.bench-grid {
    display:grid; grid-template-columns:1fr 1fr; gap:0.85rem; margin:1.2rem 0;
}
.bench-metric-card {
    background:#111111; border:1px solid rgba(255,255,255,0.07);
    padding:1.0rem 1.1rem 0.9rem;
}
.bench-metric-title {
    font-size:0.60rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:rgba(255,255,255,0.35);
    margin-bottom:0.55rem;
}
.bench-metric-row { display:flex; align-items:baseline; gap:0.55rem; flex-wrap:wrap; }
.bench-metric-user {
    font-family:'Inter',sans-serif; font-size:1.45rem; font-weight:800;
    color:#FFFFFF; line-height:1;
}
.bench-metric-vs { font-size:0.60rem; color:rgba(255,255,255,0.25); }
.bench-metric-industry { font-size:0.85rem; font-weight:600; color:rgba(255,255,255,0.45); }
.bench-metric-delta { font-size:0.72rem; font-weight:700; margin-top:0.4rem; }

/* Grade chips */
.bench-grade-crushing { color:#00E5A0; }
.bench-grade-above    { color:#7DFFCC; }
.bench-grade-on_par   { color:#FFB020; }
.bench-grade-below    { color:#FCB045; }
.bench-grade-lagging  { color:#FF3D71; }

/* Opportunity cards */
.bench-opp-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.85rem; margin:1.0rem 0; }
.bench-opp-card {
    background:#111111; border:1px solid rgba(252,176,69,0.18);
    padding:1.0rem 1.1rem;
}
.bench-opp-title {
    font-size:0.60rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:#FCB045; margin-bottom:0.45rem;
}
.bench-opp-metric { font-family:'Inter',sans-serif; font-size:1.1rem; font-weight:800; color:#FFFFFF; }
.bench-opp-gap    { font-size:0.78rem; color:rgba(255,255,255,0.45); margin-top:0.25rem; }
.bench-opp-target {
    font-size:0.68rem; font-weight:700; color:#FCB045;
    margin-top:0.5rem; letter-spacing:0.06em;
}

/* Strongest metric chip */
.bench-strongest {
    display:inline-flex; align-items:center; gap:0.45rem;
    background:rgba(0,229,160,0.07); border:1px solid rgba(0,229,160,0.18);
    padding:0.28rem 0.75rem; margin:0.6rem 0 1.2rem;
    font-size:0.62rem; font-weight:700; letter-spacing:0.12em;
    text-transform:uppercase; color:#00E5A0;
}

/* Category table */
.bench-cat-table { margin:0.6rem 0 1.0rem; }
.bench-cat-header {
    display:grid; grid-template-columns:2fr 1fr 1fr 1fr;
    padding:0.3rem 0; border-bottom:1px solid rgba(255,255,255,0.08);
    font-size:0.58rem; font-weight:700; letter-spacing:0.12em;
    text-transform:uppercase; color:rgba(255,255,255,0.28);
}
.bench-cat-row {
    display:grid; grid-template-columns:2fr 1fr 1fr 1fr;
    padding:0.55rem 0; border-bottom:1px solid rgba(255,255,255,0.05);
    align-items:center;
}
.bench-cat-row:last-child { border-bottom:none; }
.bench-cat-name { font-size:0.78rem; font-weight:600; color:#FFFFFF; }
.bench-cat-val  { font-size:0.78rem; color:rgba(255,255,255,0.70); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────────
def render_auth_page():
    st.markdown('<div class="auth-ambient"></div>', unsafe_allow_html=True)

    _, center, _ = st.columns([0.3, 2, 0.3])
    with center:
        # ── NEW SVG LOGO ─────────────────────────────
        st.markdown(
            '<div class="auth-brand" style="text-align:center;padding:3rem 0 1.75rem;">'
            + theme_engine.get_logo_html(font_size="2.4rem", tagline=True)
            + '</div>',
            unsafe_allow_html=True,
        )

        # ── CARD ─────────────────────────────────────
        with st.container(border=True):

            # ═══ FORGOT PASSWORD MODE ════════════════
            if st.session_state.forgot_pw_mode:
                st.markdown("""
                <div class="forgot-panel-header">
                    <div class="forgot-panel-title">Reset Password</div>
                    <div class="forgot-panel-sub">
                        Enter your email and we'll send a secure link to reset your password.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                fp_email = st.text_input(
                    "Email Address", placeholder="name@example.com", key="fp_email"
                )
                st.markdown("<div style='margin-top:0.65rem'></div>", unsafe_allow_html=True)

                if not st.session_state.forgot_pw_sent:
                    if st.button("Send Reset Link", use_container_width=True,
                                 type="primary", key="fp_send"):
                        if not fp_email:
                            st.error("Please enter your email address.")
                        else:
                            with st.spinner("Sending reset link..."):
                                ok, err = reset_password_email(fp_email.strip())
                            if err:
                                st.error(f"Could not send reset email: {err}")
                            else:
                                st.session_state.forgot_pw_sent = True
                                st.rerun()
                else:
                    st.markdown("""
                    <div class="save-success">
                        <span>✓</span>
                        <span>Reset link sent! Check your inbox and spam folder.</span>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='margin-top:1.1rem'></div>", unsafe_allow_html=True)
                st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
                if st.button("← Back to Login", key="fp_back"):
                    st.session_state.forgot_pw_mode = False
                    st.session_state.forgot_pw_sent = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            # ═══ NORMAL LOGIN / SIGNUP ════════════════
            else:
                login_tab, signup_tab = st.tabs(["  LOG IN  ", "  SIGN UP  "])

                # ── LOG IN ──────────────────────────────
                with login_tab:
                    li_email = st.text_input(
                        "Email Address", placeholder="name@example.com", key="li_email"
                    )
                    show_li = st.checkbox("Show password", key="show_li")
                    li_pass = st.text_input(
                        "Password",
                        type="text" if show_li else "password",
                        placeholder="Enter your password",
                        key="li_pass",
                    )

                    # Forgot password — right-aligned tiny link button
                    _, fp_col = st.columns([3, 1])
                    with fp_col:
                        st.markdown('<div class="forgot-link-btn">', unsafe_allow_html=True)
                        if st.button("Forgot?", key="forgot_btn", use_container_width=True):
                            st.session_state.forgot_pw_mode = True
                            st.session_state.forgot_pw_sent = False
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if st.button("Log In to Reel IQ", use_container_width=True,
                                 type="primary", key="li_btn"):
                        if not li_email or not li_pass:
                            st.error("Please enter your email and password.")
                        else:
                            with st.spinner("Signing you in..."):
                                response, error = sign_in(li_email.strip(), li_pass)
                            if error:
                                st.error(f"Login failed: {error}")
                            else:
                                st.session_state.authenticated = True
                                st.session_state.user_id       = response.user.id
                                st.session_state.user_email    = response.user.email
                                st.session_state.access_token  = response.session.access_token
                                st.session_state.refresh_token = response.session.refresh_token
                                st.rerun()

                # ── SIGN UP ─────────────────────────────
                with signup_tab:
                    su_email = st.text_input(
                        "Email Address", placeholder="name@example.com", key="su_email"
                    )
                    show_su = st.checkbox("Show passwords", key="show_su")
                    su_pass1 = st.text_input(
                        "Create Password",
                        type="text" if show_su else "password",
                        placeholder="8+ characters",
                        key="su_pass1",
                    )
                    su_pass2 = st.text_input(
                        "Confirm Password",
                        type="text" if show_su else "password",
                        placeholder="Repeat password",
                        key="su_pass2",
                    )
                    st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
                    if st.button("Create My Reel IQ Account", use_container_width=True,
                                 type="primary", key="su_btn"):
                        if not su_email or not su_pass1 or not su_pass2:
                            st.error("Please fill in all fields.")
                        elif su_pass1 != su_pass2:
                            st.error("Passwords don't match.")
                        elif len(su_pass1) < 8:
                            st.error("Password must be at least 8 characters.")
                        else:
                            with st.spinner("Creating your account..."):
                                response2, error2 = sign_up(su_email.strip(), su_pass1)
                            if error2:
                                st.error(f"Sign up failed: {error2}")
                            elif response2.session:
                                st.session_state.authenticated = True
                                st.session_state.user_id       = response2.user.id
                                st.session_state.user_email    = response2.user.email
                                st.session_state.access_token  = response2.session.access_token
                                st.session_state.refresh_token = response2.session.refresh_token
                                st.rerun()
                            else:
                                st.success(
                                    "✓ Account created! Check your email to confirm, then log in."
                                )

            st.markdown("""
            <div class="auth-footer">
                <p>Built for Instagram creators under 1,000 followers.<br>
                Specific diagnostics. Zero jargon.</p>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# CSV IMPORT TAB
# ─────────────────────────────────────────────────
def render_csv_import():
    how_html = (
        '<p style="font-size:0.875rem;color:#888888;line-height:1.75;margin:0 0 0.85rem;">'
        'Upload a CSV export from Meta Business Suite to import multiple reels at once. '
        'Column names are detected automatically.</p>'
        '<ol style="font-size:0.82rem;color:#888888;line-height:2.1;margin:0;padding-left:1.25rem;">'
        '<li>Go to <span style="color:rgba(255,255,255,0.65);">Meta Business Suite → Insights → Content</span></li>'
        '<li>Filter by <span style="color:rgba(255,255,255,0.65);">Reels</span> and set your date range</li>'
        '<li>Click <span style="color:rgba(255,255,255,0.65);">Export → Export as CSV</span></li>'
        '<li>Upload the file below</li>'
        '</ol>'
    )
    st.markdown(theme_engine.rio_card("How It Works", how_html), unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop your CSV here or click to browse",
        type=["csv"],
        help="Export from Meta Business Suite → Insights → Content → Reels → Export",
    )

    if uploaded is None:
        st.markdown("""
        <div style="text-align:center; padding: 2.75rem 1rem; color:rgba(255,255,255,0.15); font-size:0.82rem;">
            No file uploaded yet. Export your Reels CSV from Meta Business Suite and drop it above.
        </div>
        """, unsafe_allow_html=True)
        return

    try:
        df = pd.read_csv(uploaded, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
    except Exception as e:
        st.error(f"Could not read CSV: {e}.")
        return

    if df.empty:
        st.error("The CSV file is empty.")
        return

    total_rows = len(df)
    col_map = build_column_map(df.columns.tolist())

    st.markdown('<div class="section-label">Detected Columns</div>', unsafe_allow_html=True)

    core_fields = ["views", "likes", "comments", "shares", "saves",
                   "watch_time_minutes", "reel_duration_seconds", "caption"]
    map_html = '<div class="col-map-grid">'
    for field in core_fields:
        found = col_map.get(field)
        label = FIELD_LABELS.get(field, field)
        if found:
            map_html += f"""
            <div class="col-map-row">
                <span class="col-map-icon">✅</span>
                <span class="col-map-field">{label}</span>
                <span class="col-map-value">{found}</span>
            </div>"""
        else:
            map_html += f"""
            <div class="col-map-row col-map-missing">
                <span class="col-map-icon">⚠️</span>
                <span class="col-map-field">{label}</span>
                <span class="col-map-value">not found</span>
            </div>"""
    map_html += "</div>"
    st.markdown(map_html, unsafe_allow_html=True)

    if col_map.get("views") is None:
        st.error("Could not detect a Views or Plays column.")
        return

    st.markdown('<div class="section-label">Data Preview</div>', unsafe_allow_html=True)
    preview_cols = [v for v in col_map.values() if v is not None]
    st.dataframe(df[preview_cols].head(5).fillna("—"), use_container_width=True, hide_index=True)
    st.markdown(
        f'<p style="font-size:0.70rem;color:rgba(255,255,255,0.22);margin-top:0.3rem;">{total_rows} reels found</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Import Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size:0.80rem;color:rgba(255,255,255,0.32);margin:-0.5rem 0 1.1rem;">'
        'These values apply to all imported reels — the CSV does not contain follower count or content category.</p>',
        unsafe_allow_html=True,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        imp_followers = st.number_input("Your Follower Count", min_value=0, value=0, step=1, key="csv_followers")
    with col_b:
        imp_category = st.selectbox("Default Category", CATEGORY_LIST, key="csv_category")
    with col_c:
        imp_hook = st.selectbox("Default Hook Type", HOOK_TYPES, key="csv_hook")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button(f"⚡  Import {total_rows} Reels", type="primary", use_container_width=True, key="csv_import_btn"):
        benchmark_cat = CATEGORY_BENCHMARK_MAP.get(imp_category, "Educational")
        progress_bar = st.progress(0)
        status_slot  = st.empty()
        success_count = skipped_count = failed_count = 0

        for i, (_, row) in enumerate(df.iterrows()):
            status_slot.markdown(
                f'<p style="text-align:center;font-size:0.80rem;color:rgba(255,255,255,0.32);">'
                f'Processing reel {i + 1} of {total_rows}...</p>',
                unsafe_allow_html=True,
            )
            progress_bar.progress((i + 1) / total_rows)
            inputs = row_to_inputs(row, col_map, imp_followers, imp_category, imp_hook)

            if inputs["views"] == 0:
                skipped_count += 1
                continue

            try:
                results = run_diagnostic(
                    views=inputs["views"], watch_time_minutes=inputs["watch_time_minutes"],
                    reel_duration_seconds=inputs["reel_duration_seconds"],
                    likes=inputs["likes"], comments=inputs["comments"],
                    shares=inputs["shares"], saves=inputs["saves"],
                    caption=inputs["caption"], category=benchmark_cat,
                    follower_count=inputs["follower_count"],
                )
            except Exception:
                failed_count += 1
                continue

            ok, _ = save_reel_analysis(
                user_id=st.session_state.user_id,
                access_token=st.session_state.access_token,
                refresh_token=st.session_state.refresh_token,
                inputs=inputs, results=results, ai_report_text="",
            )
            if ok:
                success_count += 1
            else:
                failed_count += 1

        progress_bar.empty()
        status_slot.empty()

        skipped_line = f"<p>{skipped_count} rows skipped (0 views).</p>" if skipped_count else ""
        failed_line  = f"<p>{failed_count} rows could not be saved — check your Supabase connection.</p>" if failed_count else ""
        summary_note = f'{success_count} reels saved with full performance scores. '
        if skipped_count:
            summary_note += f'{skipped_count} rows skipped (0 views). '
        if failed_count:
            summary_note += f'{failed_count} rows could not be saved — check your Supabase connection. '
        summary_note += 'Head to My Patterns once you have 5+ reels to see personalised insights.'
        summary_body = (
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1px;'
            f'background:rgba(255,255,255,0.06);border-radius:8px;overflow:hidden;margin-bottom:1rem;">'
            f'<div style="background:#111111;padding:1rem;text-align:center;">'
            f'<div style="font-size:1.75rem;font-weight:800;color:#00E5A0;">{success_count}</div>'
            f'<div style="font-size:0.58rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#888888;margin-top:0.3rem;">Imported</div></div>'
            f'<div style="background:#111111;padding:1rem;text-align:center;">'
            f'<div style="font-size:1.75rem;font-weight:800;color:#FFB020;">{skipped_count}</div>'
            f'<div style="font-size:0.58rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#888888;margin-top:0.3rem;">Skipped</div></div>'
            f'<div style="background:#111111;padding:1rem;text-align:center;">'
            f'<div style="font-size:1.75rem;font-weight:800;color:#FF3D71;">{failed_count}</div>'
            f'<div style="font-size:0.58rem;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:#888888;margin-top:0.3rem;">Failed</div></div>'
            f'</div>'
            f'<p style="font-size:0.82rem;color:#888888;line-height:1.75;margin:0;">{summary_note}</p>'
        )
        st.markdown(theme_engine.rio_card("Import Summary", summary_body), unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# SINGLE REEL DIAGNOSTIC TAB
# ─────────────────────────────────────────────────
def render_single_reel():
    st.markdown('<div class="section-label">01 — Reel Metrics</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        views          = st.number_input("Total Views",             min_value=0,   value=0,   step=1)
        watch_time     = st.number_input("Watch Time (minutes)",    min_value=0.0, value=0.0, step=0.1)
        reel_duration  = st.number_input("Reel Duration (seconds)", min_value=1,   value=15,  step=1)
        follower_count = st.number_input("Follower Count",          min_value=0,   value=0,   step=1)
    with col2:
        likes    = st.number_input("Likes",    min_value=0, value=0, step=1)
        comments = st.number_input("Comments", min_value=0, value=0, step=1)
        shares   = st.number_input("Shares",   min_value=0, value=0, step=1)
        saves    = st.number_input("Saves",    min_value=0, value=0, step=1)

    st.markdown('<div class="section-label">02 — Content Details</div>', unsafe_allow_html=True)

    col_cat, col_hook = st.columns(2)
    with col_cat:
        category  = st.selectbox("Content Category", CATEGORY_LIST)
    with col_hook:
        hook_type = st.selectbox("Hook Type Used", HOOK_TYPES)

    caption = st.text_area(
        "Caption Text",
        placeholder="Paste your full caption here — the first line is analysed for hook strength...",
        height=110,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡  Run Diagnostic", type="primary", use_container_width=True):
        if views == 0:
            st.error("Please enter your view count to run the diagnostic.")
            return

        loading_slot = st.empty()
        loading_slot.markdown("""
        <div class="loading-state">
            <div class="loading-ring"></div>
            <p class="loading-text">Analysing your content DNA...</p>
            <p class="loading-sub">Building your performance profile</p>
        </div>
        """, unsafe_allow_html=True)

        benchmark_cat = CATEGORY_BENCHMARK_MAP.get(category, "Educational")
        inputs = {
            "views": views, "watch_time_minutes": watch_time,
            "reel_duration_seconds": reel_duration, "likes": likes,
            "comments": comments, "shares": shares, "saves": saves,
            "caption": caption, "category": category,
            "hook_type": hook_type, "follower_count": follower_count,
        }

        results = run_diagnostic(
            views=views, watch_time_minutes=watch_time,
            reel_duration_seconds=reel_duration, likes=likes,
            comments=comments, shares=shares, saves=saves,
            caption=caption, category=benchmark_cat, follower_count=follower_count,
        )
        report = generate_ai_report(results)
        loading_slot.empty()

        save_ok, save_err = save_reel_analysis(
            user_id=st.session_state.user_id,
            access_token=st.session_state.access_token,
            refresh_token=st.session_state.refresh_token,
            inputs=inputs, results=results, ai_report_text=report,
        )

        retention  = results["retention"]
        engagement = results["engagement"]
        hook       = results["hook"]
        save_rate  = results["save_rate"]

        def get_tier(label):
            if label in ("Good", "Excellent", "Strong"):          return "good"
            if label in ("Average", "Moderate", "Below Average"): return "average"
            return "poor"

        r_tier = get_tier(retention["label"])
        e_tier = get_tier(engagement["label"])
        h_tier = get_tier(hook["label"])
        s_tier = get_tier(save_rate["label"])

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">03 — Performance Scores</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="score-grid">
            <div class="score-card {r_tier}">
                <div class="score-label">Retention</div>
                <div class="score-value">{round(retention['ratio']*100, 1)}%</div>
                <span class="score-tag">{retention['label']}</span>
            </div>
            <div class="score-card {e_tier}">
                <div class="score-label">Engagement</div>
                <div class="score-value">{round(engagement['rate']*100, 1)}%</div>
                <span class="score-tag">{engagement['label']}</span>
            </div>
            <div class="score-card {h_tier}">
                <div class="score-label">Hook Score</div>
                <div class="score-value">{hook['score']}<span style="font-size:1.1rem;opacity:0.22;font-weight:400">/10</span></div>
                <span class="score-tag">{hook['label']}</span>
            </div>
            <div class="score-card {s_tier}">
                <div class="score-label">Save Rate</div>
                <div class="score-value">{round(save_rate['rate']*100, 1)}%</div>
                <span class="score-tag">{save_rate['label']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if save_ok:
            st.markdown("""
            <div class="save-success">
                <span>✓</span>
                <span>Saved to your Reel IQ account — this analysis is part of your performance history.</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="save-error">
                <span>⚠</span>
                <span>Diagnostic complete, but could not save: {save_err}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">04 — Score Breakdown</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="insight-block {r_tier}">
            <div class="insight-title">Retention Analysis</div>
            <div class="insight-text">{retention['explanation']}</div>
        </div>
        <div class="insight-block {e_tier}">
            <div class="insight-title">Engagement Analysis</div>
            <div class="insight-text">{engagement['explanation']}</div>
        </div>
        <div class="insight-block {h_tier}">
            <div class="insight-title">Hook Analysis</div>
            <div class="insight-text">{hook['explanation']}</div>
        </div>
        <div class="insight-block {s_tier}">
            <div class="insight-title">Save Rate Analysis</div>
            <div class="insight-text">{save_rate['explanation']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">05 — AI Diagnostic Report</div>', unsafe_allow_html=True)

        report_body = (
            f'<div style="font-size:0.66rem;color:#888888;margin-bottom:0.85rem;">'
            f'GPT-4o mini &nbsp;·&nbsp; Calibrated for sub-10K accounts &nbsp;·&nbsp; {category}</div>'
            f'<div style="font-size:0.875rem;color:#888888;line-height:1.95;font-weight:400;white-space:pre-wrap;">{report}</div>'
        )
        st.markdown(theme_engine.rio_card("AI Analysis", report_body), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="↓  Download Full Report",
            data=report,
            file_name="reeliq_diagnostic_report.txt",
            mime="text/plain",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────
# MY PATTERNS TAB
# ─────────────────────────────────────────────────
def render_patterns():
    st.markdown("""
    <div class="patterns-hero">
        <h2>📈 My Patterns</h2>
        <p>Your personal benchmarks — based entirely on your own reels, not industry averages.</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.patterns_loaded:
        with st.spinner("Loading your reels…"):
            reels, err = get_user_reels(
                st.session_state.user_id,
                st.session_state.access_token,
                st.session_state.refresh_token,
            )
        if err:
            st.error(f"Could not load your reels: {err}")
            return
        patterns = compute_patterns(reels or [])
        st.session_state.patterns_data = patterns
        st.session_state.patterns_loaded = True

    patterns = st.session_state.patterns_data

    col_r, _ = st.columns([1, 4])
    with col_r:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="patterns_refresh"):
            st.session_state.patterns_loaded = False
            st.session_state.patterns_data = None
            st.session_state.patterns_insights = None
            st.session_state.patterns_roadmap = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if not patterns or not patterns.get("enough_data"):
        logged = patterns["count"] if patterns else 0
        needed = MIN_REELS - logged
        st.markdown(f"""
        <div class="patterns-gate">
            <span class="gate-count">{logged} / {MIN_REELS}</span>
            <h3>Keep logging your reels</h3>
            <p>You need <strong style="color:rgba(255,255,255,0.70);">{needed} more reel{"s" if needed != 1 else ""}</strong> before
            patterns become visible. The more you log, the smarter your insights get.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    b = patterns["benchmarks"]
    count = patterns["count"]

    st.markdown(f'<div class="section-label">Your averages across {count} reels</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="bench-grid">
        <div class="bench-card bench-views">
            <div class="bench-val">{b['avg_views']:,.0f}</div>
            <div class="bench-label">Avg Views</div>
        </div>
        <div class="bench-card bench-ret">
            <div class="bench-val">{b['avg_retention']*100:.1f}%</div>
            <div class="bench-label">Avg Retention</div>
        </div>
        <div class="bench-card bench-eng">
            <div class="bench-val">{b['avg_engagement']*100:.2f}%</div>
            <div class="bench-label">Avg Engagement</div>
        </div>
        <div class="bench-card bench-save">
            <div class="bench-val">{b['avg_save_rate']*100:.2f}%</div>
            <div class="bench-label">Avg Save Rate</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    trend = patterns.get("trend", {})
    if trend:
        chg = trend["change_pct"]
        if chg > 5:
            badge_cls, arrow, label = "trend-up",   "▲", f"+{chg:.0f}% vs earlier reels"
        elif chg < -5:
            badge_cls, arrow, label = "trend-down", "▼", f"{chg:.0f}% vs earlier reels"
        else:
            badge_cls, arrow, label = "trend-flat", "→", "Steady vs earlier reels"
        st.markdown(f"""
        <div style="margin: 0.6rem 0 1.75rem;">
            <span class="trend-badge {badge_cls}">{arrow} {label}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">What your data is telling you</div>', unsafe_allow_html=True)

    if st.session_state.patterns_insights is None:
        if st.button("✨ Generate AI Insights + Priority Roadmap", key="gen_insights_btn"):
            with st.spinner("Analysing your patterns…"):
                insights, roadmap_items, err = generate_ai_content(patterns)
            if err:
                st.error(f"Could not generate insights: {err}")
            else:
                st.session_state.patterns_insights = insights
                st.session_state.patterns_roadmap  = roadmap_items or []
                st.rerun()
    else:
        insights_body = (
            f'<p style="font-size:0.875rem;color:#888888;line-height:1.9;margin:0;white-space:pre-wrap;">'
            f'{st.session_state.patterns_insights}</p>'
        )
        st.markdown(theme_engine.rio_card("AI Insights", insights_body), unsafe_allow_html=True)

        roadmap = st.session_state.patterns_roadmap or []
        if roadmap:
            st.markdown(
                '<div class="section-label" style="margin-top:2rem;">Priority Roadmap</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<p style="font-size:0.76rem;color:rgba(255,255,255,0.25);margin:-0.5rem 0 1.1rem;">'
                'Ranked by impact — do these in order to move the needle fastest.</p>',
                unsafe_allow_html=True,
            )
            for item in roadmap:
                level = item.get("level", "MEDIUM")
                title = item.get("title", "")
                desc  = item.get("desc", "")
                st.markdown(f"""
                <div class="roadmap-card roadmap-{level}">
                    <span class="priority-badge priority-{level}">{level}</span>
                    <div class="roadmap-body">
                        <div class="roadmap-title">{title}</div>
                        <div class="roadmap-desc">{desc}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("🔁 Regenerate Insights", key="regen_insights_btn"):
            st.session_state.patterns_insights = None
            st.session_state.patterns_roadmap  = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    cat_summary = patterns.get("category_summary", [])
    if cat_summary:
        st.markdown('<div class="section-label" style="margin-top:2rem;">Content Type Breakdown</div>', unsafe_allow_html=True)
        rows_html = ""
        for row in cat_summary:
            rows_html += f"""
            <tr>
                <td><strong style="color:rgba(255,255,255,0.70);">{row['category']}</strong></td>
                <td>{row['count']}</td>
                <td>{row['avg_views']:,.0f}</td>
                <td>{row['avg_saves']:.1f}</td>
                <td>{row['avg_retention']*100:.1f}%</td>
            </tr>"""
        st.markdown(f"""
        <table class="breakdown-table">
            <thead><tr>
                <th>Category</th><th>Reels</th>
                <th>Avg Views</th><th>Avg Saves</th><th>Avg Retention</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    hook_summary = patterns.get("hook_summary", [])
    if len(hook_summary) > 1:
        st.markdown('<div class="section-label" style="margin-top:2rem;">Hook Type Breakdown</div>', unsafe_allow_html=True)
        rows_html = ""
        for row in hook_summary:
            rows_html += f"""
            <tr>
                <td><strong style="color:rgba(255,255,255,0.70);">{row['hook_type']}</strong></td>
                <td>{row['count']}</td>
                <td>{row['avg_hook_score']:.1f}</td>
                <td>{row['avg_retention']*100:.1f}%</td>
            </tr>"""
        st.markdown(f"""
        <table class="breakdown-table">
            <thead><tr>
                <th>Hook Type</th><th>Reels</th>
                <th>Avg Hook Score</th><th>Avg Retention</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    top = patterns.get("top_performers", [])
    if top:
        st.markdown('<div class="section-label" style="margin-top:2rem;">Top Performers</div>', unsafe_allow_html=True)
        for r in top:
            caption = r.get("caption") or r.get("category") or "Untitled"
            st.markdown(f"""
            <div class="top-reel-card">
                <div class="reel-caption">{caption[:90]}</div>
                <div class="reel-stats">
                    <span class="reel-stat-pill">👁 {r.get('views',0):,} views</span>
                    <span class="reel-stat-pill">💾 {r.get('saves',0):,} saves</span>
                    <span class="reel-stat-pill">📊 {(r.get('retention_ratio') or 0)*100:.0f}% retention</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    under = patterns.get("underperformers", [])
    if under:
        st.markdown(
            f'<div class="section-label" style="margin-top:2rem;">Underperformers '
            f'<span style="color:rgba(255,255,255,0.18);font-weight:400;text-transform:none;letter-spacing:0;">'
            f'(under {b["avg_views"]*0.6:,.0f} views)</span></div>',
            unsafe_allow_html=True,
        )
        for r in under:
            caption = r.get("caption") or r.get("category") or "Untitled"
            st.markdown(f"""
            <div class="top-reel-card under-card">
                <div class="reel-caption">{caption[:90]}</div>
                <div class="reel-stats">
                    <span class="reel-stat-pill">👁 {r.get('views',0):,} views</span>
                    <span class="reel-stat-pill">💾 {r.get('saves',0):,} saves</span>
                    <span class="reel-stat-pill">📊 {(r.get('retention_ratio') or 0)*100:.0f}% retention</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# PRE-SCORE  ·  Phase 4
# ─────────────────────────────────────────────────
HOOK_TYPES = [
    "Question",
    "Bold Statement",
    "Tutorial / How-To",
    "Story / Narrative",
    "Challenge / Trend",
    "Behind the Scenes",
    "No Hook Planned",
]

CATEGORIES = ["Educational", "Inspirational", "Transactional", "Aesthetic", "Entertainment"]


def _prescore_ring_html(score: int, colour: str) -> str:
    """Render the circular score ring as inline HTML/SVG."""
    r = 60
    circ = 2 * 3.14159 * r
    fill = circ - (score / 100) * circ
    grad_id = "ringGrad"
    if colour == "good":
        stroke = f"url(#{grad_id})"
        num_cls = "good"
    elif colour == "average":
        stroke = "#FFB020"
        num_cls = "average"
    else:
        stroke = "#FF3D71"
        num_cls = "poor"

    return f"""
    <div class="prescore-ring-wrap">
        <div class="prescore-ring">
            <svg width="148" height="148" viewBox="0 0 148 148">
                <defs>
                    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#FF00FF"/>
                        <stop offset="100%" stop-color="#FF8C00"/>
                    </linearGradient>
                </defs>
                <circle class="prescore-ring-bg" cx="74" cy="74" r="{r}"/>
                <circle class="prescore-ring-fill {colour}"
                    cx="74" cy="74" r="{r}"
                    stroke="{stroke}"
                    stroke-dasharray="{circ:.2f}"
                    stroke-dashoffset="{fill:.2f}"
                    transform="rotate(-90 74 74)"
                    style="fill:none;stroke-width:8;stroke-linecap:butt;"/>
            </svg>
            <div class="prescore-inner">
                <span class="prescore-number {num_cls}">{score}</span>
                <span class="prescore-label">/ 100</span>
            </div>
        </div>
    </div>"""


def render_pre_score():
    st.markdown("""
    <div class="prescore-hero">
        <div class="prescore-hero-title">Plan Before You Film</div>
        <div class="prescore-hero-sub">Get a predicted performance score before you hit record —
        so you optimise your reel before it's too late to change it.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── INPUT FORM ────────────────────────────────
    st.markdown('<div class="section-label">Your Planned Reel</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox(
            "Content Category",
            CATEGORIES,
            key="ps_category",
            help="What type of content is this reel?",
        )
    with col2:
        hook_type = st.selectbox(
            "Hook Type",
            HOOK_TYPES,
            key="ps_hook_type",
            help="How will you open the first 3 seconds?",
        )

    col3, col4 = st.columns(2)
    with col3:
        duration = st.number_input(
            "Planned Duration (seconds)",
            min_value=5, max_value=300, value=30, step=5,
            key="ps_duration",
        )
    with col4:
        followers = st.number_input(
            "Your Follower Count",
            min_value=0, max_value=10_000_000, value=1000, step=100,
            key="ps_followers",
        )

    planned_caption = st.text_area(
        "Planned Caption Opening Line (optional)",
        placeholder="e.g. 'Stop scrolling if you want to double your reach...'",
        key="ps_caption",
        height=80,
        help="Enter just the first line of your planned caption — we'll score its hook strength.",
    )

    st.markdown("<div style='margin-top:0.9rem'></div>", unsafe_allow_html=True)

    if st.button("⚡ Calculate Pre-Score", use_container_width=True, key="ps_run_btn"):
        result = run_pre_score(
            category=category,
            hook_type=hook_type,
            planned_duration_seconds=int(duration),
            follower_count=int(followers),
            planned_caption=planned_caption.strip(),
        )
        st.session_state["ps_result"] = result
        st.session_state["ps_tips"] = None  # reset tips

    # ── RESULTS ───────────────────────────────────
    result = st.session_state.get("ps_result")
    if not result:
        return

    total   = result["total"]
    colour  = result["colour"]
    label   = result["label"]
    summary = result["summary"]
    comps   = result["components"]
    flags   = result["flags"]

    st.markdown('<div class="section-label" style="margin-top:2rem;">Pre-Score Result</div>', unsafe_allow_html=True)

    # Ring + verdict centred
    st.markdown(_prescore_ring_html(total, colour), unsafe_allow_html=True)
    verdict_colour = {"good": "#00E5A0", "average": "#FFB020", "poor": "#FF3D71"}.get(colour, "#FFFFFF")
    st.markdown(
        f'<p style="text-align:center;margin:-0.5rem 0 0.3rem;">'
        f'<span style="font-family:\'Syne\',sans-serif;font-weight:800;font-size:0.9rem;'
        f'color:{verdict_colour};">{label}</span></p>'
        f'<p style="text-align:center;font-size:0.79rem;color:rgba(255,255,255,0.36);'
        f'margin-bottom:1.4rem;">{summary}</p>',
        unsafe_allow_html=True,
    )

    # Component bars
    st.markdown('<div class="prescore-components">', unsafe_allow_html=True)
    for key, comp in comps.items():
        pct = (comp["score"] / 25) * 100
        st.markdown(f"""
        <div class="prescore-comp">
            <div class="prescore-comp-top">
                <span class="prescore-comp-name">{comp['label']}</span>
                <span class="prescore-comp-val">{comp['score']}<span style="font-size:0.65rem;color:rgba(255,255,255,0.28);font-family:'Inter',sans-serif;font-weight:400;">/25</span></span>
            </div>
            <div class="prescore-bar-track">
                <div class="prescore-bar-fill" style="width:{pct:.0f}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Risk flags
    if flags:
        st.markdown(
            '<div class="section-label" style="margin-top:1.75rem;">Risk Flags</div>',
            unsafe_allow_html=True,
        )
        for flag in flags:
            st.markdown(f"""
            <div class="risk-flag">
                <span class="risk-icon">⚠</span>
                <span class="risk-text">{flag}</span>
            </div>
            """, unsafe_allow_html=True)

    # AI Tips
    st.markdown(
        '<div class="section-label" style="margin-top:1.75rem;">AI Pre-Production Tips</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("ps_tips") is None:
        if st.button("✨ Generate AI Tips", use_container_width=True, key="ps_tips_btn"):
            with st.spinner("Generating pre-production tips…"):
                tips = generate_pre_score_tips(result)
            st.session_state["ps_tips"] = tips
            st.rerun()
    else:
        tips_body = (
            f'<div style="font-size:0.66rem;color:#888888;margin-bottom:0.75rem;">'
            f'Generated by GPT-4o-mini · based on your planned reel</div>'
            f'<div style="font-size:0.875rem;color:#888888;line-height:1.9;white-space:pre-wrap;">'
            f'{st.session_state["ps_tips"]}</div>'
        )
        st.markdown(theme_engine.rio_card("AI Recommendations", tips_body), unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.85rem;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("🔁 Regenerate Tips", key="ps_regen_btn"):
            st.session_state["ps_tips"] = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# CONTENT BRIEF  ·  Phase 5
# ─────────────────────────────────────────────────
_GOALS = [
    "More Views / Reach",
    "More Saves (evergreen value)",
    "More Engagement (comments & shares)",
    "Grow Followers",
    "Drive Website / Link Traffic",
]

_BRIEF_SECTIONS = [
    ("FORMAT",        "━━ FORMAT"),
    ("HOOK OPTIONS",  "━━ HOOK OPTIONS"),
    ("CAPTION",       "━━ CAPTION STRUCTURE"),
    ("ANGLE",         "━━ CONTENT ANGLE"),
    ("FILMING",       "━━ FILMING NOTES"),
]


def _parse_brief(raw: str) -> dict:
    """Split raw brief text into labelled sections."""
    markers = [s[1] for s in _BRIEF_SECTIONS]
    sections = {}
    current_key = None
    current_lines = []

    for line in raw.splitlines():
        stripped = line.strip()
        matched = False
        for marker in markers:
            if stripped.startswith(marker):
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = marker
                current_lines = []
                matched = True
                break
        if not matched and current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def _render_brief_card(raw: str, topic: str, goal: str, is_personalised: bool):
    sections = _parse_brief(raw)

    chip_cls  = "brief-data-chip" if is_personalised else "brief-data-chip generic"
    chip_text = "✓ Personalised from your data" if is_personalised else "⚠ Generic brief — log 5+ reels to personalise"

    st.markdown(f'<div class="{chip_cls}">{chip_text}</div>', unsafe_allow_html=True)

    # Build all content as a single HTML string for rio_card
    content_html = (
        f'<div style="font-size:0.66rem;color:#888888;margin-bottom:0.3rem;">'
        f'Generated by GPT-4o-mini · goal: {goal}</div>'
        f'<div style="font-size:0.92rem;font-weight:700;color:rgba(255,255,255,0.80);margin-bottom:1.2rem;">{topic[:60]}</div>'
    )

    # FORMAT section → render as pills
    fmt_raw = sections.get("━━ FORMAT", "")
    if fmt_raw:
        pills_html = ""
        for line in fmt_raw.splitlines():
            if ":" in line:
                label, val = line.split(":", 1)
                pills_html += (
                    f'<div class="brief-format-pill">'
                    f'{label.strip()}: <span>{val.strip()}</span>'
                    f'</div>'
                )
        content_html += (
            f'<div class="brief-section">'
            f'<div class="brief-section-label">Format</div>'
            f'<div class="brief-format-pills">{pills_html}</div>'
            f'</div>'
        )

    # HOOK OPTIONS → render as styled option blocks
    hooks_raw = sections.get("━━ HOOK OPTIONS", "")
    if hooks_raw:
        hooks_html = ""
        for line in hooks_raw.splitlines():
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                text = line.lstrip("0123456789.-) ").strip().strip('"')
                hooks_html += f'<div class="brief-hook-option">"{text}"</div>'
        content_html += (
            f'<div class="brief-section">'
            f'<div class="brief-section-label">Hook Options — Pick One</div>'
            + hooks_html +
            f'</div>'
        )

    # CAPTION STRUCTURE
    cap_raw = sections.get("━━ CAPTION STRUCTURE", "")
    if cap_raw:
        content_html += (
            f'<div class="brief-section">'
            f'<div class="brief-section-label">Caption Structure</div>'
            f'<div class="brief-section-body">{cap_raw}</div>'
            f'</div>'
        )

    # CONTENT ANGLE
    angle_raw = sections.get("━━ CONTENT ANGLE", "")
    if angle_raw:
        content_html += (
            f'<div class="brief-section">'
            f'<div class="brief-section-label">Content Angle</div>'
            f'<div class="brief-section-body">{angle_raw}</div>'
            f'</div>'
        )

    # FILMING NOTES
    film_raw = sections.get("━━ FILMING NOTES", "")
    if film_raw:
        content_html += (
            f'<div class="brief-section">'
            f'<div class="brief-section-label">Filming Notes</div>'
            f'<div class="brief-section-body">{film_raw}</div>'
            f'</div>'
        )

    # If sections were not parsed (GPT didn't follow format), show raw
    if not any(sections.values()):
        content_html += f'<div class="brief-section"><div class="brief-section-body">{raw}</div></div>'

    st.markdown(theme_engine.rio_card("Content Brief", content_html), unsafe_allow_html=True)


def render_content_brief():
    st.markdown("""
    <div class="brief-hero">
        <div class="brief-hero-title">Content Brief Generator</div>
        <div class="brief-hero-sub">Tell us your topic and goal — we'll build a production-ready
        brief tailored to what actually works for your account.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load patterns silently if available ──────
    patterns = st.session_state.get("patterns_data")
    is_personalised = bool(patterns and patterns.get("enough_data"))

    if not is_personalised:
        # Try to fetch quietly
        uid   = st.session_state.get("user_id")
        atk   = st.session_state.get("access_token")
        rtk   = st.session_state.get("refresh_token")
        if uid and atk and rtk:
            from supabase_client import get_user_reels
            from patterns import compute_patterns
            reels, _ = get_user_reels(uid, atk, rtk)
            if reels:
                patterns = compute_patterns(reels or [])
                st.session_state.patterns_data   = patterns
                st.session_state.patterns_loaded = True
                is_personalised = bool(patterns and patterns.get("enough_data"))

    # Personalisation status banner
    if is_personalised:
        b = patterns["benchmarks"]
        st.markdown(
            f'<div class="brief-data-chip">✓ Personalised · {patterns["count"]} reels · '
            f'{b["avg_retention"]*100:.0f}% avg retention · '
            f'Best hook: {patterns["hook_summary"][0]["hook_type"] if patterns.get("hook_summary") else "N/A"}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        reel_count = patterns["count"] if patterns else 0
        needed = max(0, 5 - reel_count)
        st.markdown(
            f'<div class="brief-data-chip generic">⚠ Generic mode — log {needed} more reel'
            f'{"s" if needed != 1 else ""} to personalise this brief to your data</div>',
            unsafe_allow_html=True,
        )

    # ── INPUT FORM ────────────────────────────────
    st.markdown('<div class="section-label">Brief Details</div>', unsafe_allow_html=True)

    topic = st.text_input(
        "Reel Topic / Theme",
        placeholder="e.g. 'Morning routine for productivity', 'How I grew my page to 10k'",
        key="brief_topic_input",
        value=st.session_state.get("brief_topic", ""),
    )

    goal = st.selectbox(
        "Primary Goal",
        _GOALS,
        key="brief_goal_input",
        help="What do you most want this reel to achieve?",
    )

    st.markdown("<div style='margin-top:0.9rem'></div>", unsafe_allow_html=True)

    run_col, regen_col = st.columns([3, 1])
    with run_col:
        generate_clicked = st.button(
            "📝 Generate Content Brief",
            use_container_width=True,
            key="brief_generate_btn",
        )
    with regen_col:
        st.markdown('<div class="ghost-btn" style="margin-top:0;">', unsafe_allow_html=True)
        regen_clicked = st.button("🔁 Regenerate", key="brief_regen_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    should_generate = generate_clicked or (
        regen_clicked and st.session_state.get("brief_result")
    )

    if should_generate:
        if not topic.strip():
            st.warning("Please enter a topic for your reel.")
            return
        with st.spinner("Writing your personalised brief…"):
            raw = generate_content_brief(
                topic=topic.strip(),
                goal=goal,
                patterns=patterns if is_personalised else None,
            )
        st.session_state["brief_result"]    = raw
        st.session_state["brief_topic"]     = topic.strip()
        st.session_state["brief_goal"]      = goal
        st.session_state["brief_personalised"] = is_personalised
        st.rerun()

    # ── RESULT ────────────────────────────────────
    brief_raw = st.session_state.get("brief_result")
    if not brief_raw:
        return

    st.markdown(
        '<div class="section-label" style="margin-top:2rem;">Your Brief</div>',
        unsafe_allow_html=True,
    )
    _render_brief_card(
        raw=brief_raw,
        topic=st.session_state.get("brief_topic", topic),
        goal=st.session_state.get("brief_goal", goal),
        is_personalised=st.session_state.get("brief_personalised", is_personalised),
    )


# ─────────────────────────────────────────────────
# WEEKLY DIGEST  ·  Phase 6
# ─────────────────────────────────────────────────
def _trend_label(val):
    if val is None:
        return ""
    if val > 3:
        return f'<span class="digest-trend-up">▲ +{val:.0f}%</span>'
    if val < -3:
        return f'<span class="digest-trend-down">▼ {val:.0f}%</span>'
    return f'<span class="digest-trend-flat">→ {val:+.0f}%</span>'


def render_weekly_digest():
    st.markdown("""
    <div class="digest-hero">
        <div class="digest-hero-title">Weekly Performance Digest</div>
        <div class="digest-hero-sub">A snapshot of your reel performance —
        preview it here and send it straight to your inbox.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load reel data ────────────────────────────
    uid = st.session_state.get("user_id")
    atk = st.session_state.get("access_token")
    rtk = st.session_state.get("refresh_token")
    email = st.session_state.get("user_email", "")

    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button("🔄 Generate Digest", use_container_width=True, key="digest_gen_btn"):
            with st.spinner("Building your digest…"):
                reels, err = get_user_reels(uid, atk, rtk)
            if err or not reels:
                st.error("Could not load your reels. Check your connection and try again.")
                return
            d = build_digest_data(reels, email)
            st.session_state["digest_data"] = d
            st.session_state["digest_sent"] = False
            st.session_state["digest_send_msg"] = ""
            st.rerun()

    d = st.session_state.get("digest_data")
    if not d:
        st.markdown(
            '<p style="font-size:0.78rem;color:rgba(255,255,255,0.25);margin-top:0.6rem;">'
            'Hit Generate to compute your digest from your logged reels.</p>',
            unsafe_allow_html=True,
        )
        return

    if not d.get("has_data"):
        st.warning("No reels logged yet. Analyse and save at least one reel first.")
        return

    # ── PERIOD HEADER ─────────────────────────────
    period_note = ""
    if d.get("is_all_time"):
        period_note = (
            f'<span style="font-size:0.64rem;color:rgba(255,176,32,0.65);margin-left:0.5rem;">'
            f'(all time — log more reels for a weekly snapshot)</span>'
        )

    st.markdown(
        f'<div class="section-label" style="margin-top:0.5rem;">'
        f'{d["period_label"]}{period_note}</div>',
        unsafe_allow_html=True,
    )

    # ── METRIC GRID ───────────────────────────────
    v_trend = _trend_label(d.get("view_trend"))
    r_trend = _trend_label(d.get("ret_trend"))

    st.markdown(f"""
    <div class="digest-stat-row">
        <div class="digest-stat">
            <div class="digest-stat-val">{d['reel_count']}</div>
            <div class="digest-stat-label">Reels</div>
        </div>
        <div class="digest-stat">
            <div class="digest-stat-val">{d['avg_views']:,.0f}</div>
            <div class="digest-stat-label">Avg Views {v_trend}</div>
        </div>
        <div class="digest-stat">
            <div class="digest-stat-val">{d['avg_retention']}%</div>
            <div class="digest-stat-label">Avg Retention {r_trend}</div>
        </div>
        <div class="digest-stat">
            <div class="digest-stat-val">{d['total_saves']:,}</div>
            <div class="digest-stat-label">Total Saves</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── BEST & WORST ──────────────────────────────
    best  = d.get("best_reel")
    worst = d.get("worst_reel")

    if best:
        b_cap = (best.get("caption") or best.get("category") or "Untitled")[:80]
        b_views = f'{best.get("views", 0):,}'
        b_ret   = f'{(best.get("retention_ratio") or 0)*100:.0f}%'
        b_hook  = best.get("hook_label") or best.get("hook_type") or "—"
        st.markdown(f"""
        <div class="digest-reel-card best">
            <div class="digest-reel-badge">🏆 Best Reel This Period</div>
            <div class="digest-reel-caption">"{b_cap}"</div>
            <div class="digest-reel-stats">{b_views} views · {b_ret} retention · Hook: {b_hook}</div>
        </div>
        """, unsafe_allow_html=True)

    if worst and worst != best:
        w_cap  = (worst.get("caption") or worst.get("category") or "Untitled")[:80]
        w_views = f'{worst.get("views", 0):,}'
        w_ret   = worst.get("retention_label") or "—"
        w_eng   = worst.get("engagement_label") or "—"
        st.markdown(f"""
        <div class="digest-reel-card worst">
            <div class="digest-reel-badge">⚠ Needs Attention</div>
            <div class="digest-reel-caption">"{w_cap}"</div>
            <div class="digest-reel-stats">{w_views} views · Retention: {w_ret} · Engagement: {w_eng}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── FOCUS TIP ─────────────────────────────────
    if d.get("best_category"):
        tip_body = (
            f'<div style="font-size:0.82rem;color:#888888;line-height:1.75;">'
            f'Your best-performing category is <strong style="color:rgba(255,255,255,0.72);">'
            f'{d["best_category"]}</strong>. Create at least one more reel in this category '
            f'and experiment with a <strong style="color:rgba(255,255,255,0.72);">Question</strong> '
            f'or <strong style="color:rgba(255,255,255,0.72);">Tutorial / How-To</strong> hook '
            f'to push past your current {d["avg_retention"]}% retention baseline.'
            f'</div>'
        )
        st.markdown(theme_engine.rio_card("Focus Tip", tip_body, "success"), unsafe_allow_html=True)

    # ── SEND SECTION ──────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:1.75rem;">Send to Inbox</div>', unsafe_allow_html=True)

    has_resend = bool(_get_resend_key_ui())

    if has_resend:
        send_col, regen_col = st.columns([2, 1])
        with send_col:
            if st.button(
                f"📧 Send Digest to {email}",
                use_container_width=True,
                key="digest_send_btn",
                disabled=st.session_state.get("digest_sent", False),
            ):
                with st.spinner("Sending…"):
                    ok, msg = send_digest_email(email, d)
                st.session_state["digest_sent"] = ok
                st.session_state["digest_send_msg"] = msg
                st.rerun()

        with regen_col:
            st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
            if st.button("🔄 Refresh", key="digest_refresh_btn", use_container_width=True):
                st.session_state["digest_data"] = None
                st.session_state["digest_sent"] = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("digest_sent"):
            st.markdown("""
            <div class="save-success" style="margin-top:0.7rem;">
                ✓ Digest sent — check your inbox!
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.get("digest_send_msg") and not st.session_state.get("digest_sent"):
            st.error(f"Send failed: {st.session_state['digest_send_msg']}")
    else:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("🔄 Refresh Digest", key="digest_refresh_btn2", use_container_width=True):
            st.session_state["digest_data"] = None
            st.session_state["digest_sent"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="digest-setup-note">
            <strong style="color:rgba(255,176,32,0.85);">Email sending not configured.</strong>
            To send this digest to your inbox, add your Resend API key to
            <code>.streamlit/secrets.toml</code>:<br><br>
            <code>RESEND_API_KEY = "re_xxxxxxxxxxxx"</code><br><br>
            Get a free key at <strong>resend.com</strong> (3,000 emails/month free).
            Your digest above is fully generated — just email delivery needs setup.
        </div>
        """, unsafe_allow_html=True)


def _get_resend_key_ui() -> str:
    """Helper visible to render functions."""
    try:
        import streamlit as st
        return st.secrets.get("RESEND_API_KEY", "")
    except Exception:
        return os.getenv("RESEND_API_KEY", "")


# ─────────────────────────────────────────────────
# MONTHLY CARD  ·  Phase 7
# ─────────────────────────────────────────────────
from calendar import month_name as _month_name

def _monthly_ring_html(score: int, colour: str) -> str:
    r = 36
    circ = 2 * 3.14159 * r
    fill = circ - (score / 100) * circ
    stroke = "url(#mRingGrad)" if colour == "good" else ("#FFB020" if colour == "average" else "#FF3D71")
    num_cls = colour
    return (
        f'<div class="monthly-score-ring">'
        f'<svg width="88" height="88" viewBox="0 0 88 88">'
        f'<defs><linearGradient id="mRingGrad" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="#FF00FF"/>'
        f'<stop offset="100%" stop-color="#FF8C00"/>'
        f'</linearGradient></defs>'
        f'<circle fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="6" cx="44" cy="44" r="{r}"/>'
        f'<circle fill="none" stroke="{stroke}" stroke-width="6" stroke-linecap="butt"'
        f' cx="44" cy="44" r="{r}"'
        f' stroke-dasharray="{circ:.2f}" stroke-dashoffset="{fill:.2f}"'
        f' transform="rotate(-90 44 44)"/>'
        f'</svg>'
        f'<div class="monthly-score-inner">'
        f'<span class="monthly-score-num {num_cls}">{score}</span>'
        f'<span class="monthly-score-lbl">score</span>'
        f'</div></div>'
    )


def _change_class(val):
    if val is None:
        return "flat", "—"
    if val > 3:
        return "up", f"▲ +{val:.0f}%"
    if val < -3:
        return "down", f"▼ {val:.0f}%"
    return "flat", f"→ {val:+.0f}%"


def render_monthly_card():
    st.markdown("""
    <div class="monthly-hero">
        <div class="monthly-hero-title">Monthly Performance Card</div>
        <div class="monthly-hero-sub">Your Spotify Wrapped for Instagram Reels —
        month-over-month growth, your best content, and a single Growth Score.</div>
    </div>
    """, unsafe_allow_html=True)

    uid = st.session_state.get("user_id")
    atk = st.session_state.get("access_token")
    rtk = st.session_state.get("refresh_token")

    # ── Month selector + generate button ─────────
    st.markdown('<div class="section-label">Select Month</div>', unsafe_allow_html=True)

    # Fetch reels once to know available months
    all_reels = None
    if st.session_state.get("patterns_data"):
        # Reuse if patterns already loaded (won't have full reel list, so we still need to fetch)
        pass

    sel_col, btn_col = st.columns([2, 1])
    with sel_col:
        from datetime import datetime as _dt
        now = _dt.now()
        # Build month options: current month back 11 months
        month_options = []
        for i in range(12):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            month_options.append((y, m, f"{_month_name[m]} {y}"))

        month_labels  = [o[2] for o in month_options]
        selected_label = st.selectbox(
            "Month", month_labels, key="monthly_month_select", label_visibility="collapsed"
        )
        sel = next(o for o in month_options if o[2] == selected_label)
        sel_year, sel_month = sel[0], sel[1]

    with btn_col:
        generate = st.button("📊 Generate Card", use_container_width=True, key="monthly_gen_btn")

    if generate:
        with st.spinner("Building your monthly card…"):
            reels, err = get_user_reels(uid, atk, rtk)
        if err or not reels:
            st.error("Could not load your reels. Try again.")
            return
        card = compute_monthly_card(reels, target_year=sel_year, target_month=sel_month)
        st.session_state["monthly_data"]  = card
        st.session_state["monthly_year"]  = sel_year
        st.session_state["monthly_month"] = sel_month
        st.rerun()

    card = st.session_state.get("monthly_data")
    if not card:
        st.markdown(
            '<p style="font-size:0.78rem;color:rgba(255,255,255,0.25);margin-top:0.5rem;">'
            'Select a month and hit Generate to build your card.</p>',
            unsafe_allow_html=True,
        )
        return

    if not card.get("has_data"):
        st.warning("No reels found for this period.")
        return

    if card.get("use_all_time"):
        st.markdown(
            f'<div class="brief-data-chip generic" style="margin-bottom:1rem;">'
            f'⚠ Fewer than 2 reels in {card["month_label"]} — showing all-time data</div>',
            unsafe_allow_html=True,
        )

    # ── MONTH HEADER WITH GROWTH SCORE RING ──────
    ring_html = _monthly_ring_html(card["growth_score"], card["score_colour"])
    verdict_cls = card["score_colour"]

    st.markdown(f"""
    <div class="month-header">
        <div>
            <div class="month-name">{card['month_label']}</div>
            <div class="month-compare-label">vs {card['compare_label']}</div>
        </div>
        <div class="monthly-score-wrap">
            {ring_html}
            <div class="monthly-score-verdict">
                <div class="monthly-score-verdict-label {verdict_cls}">{card['score_label']}</div>
                <div class="monthly-score-verdict-sub">
                    {card['reel_count']} reel{"s" if card['reel_count'] != 1 else ""} this period<br>
                    {"Best hook: " + card['best_hook_type'] if card.get('best_hook_type') else ""}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TOTALS ────────────────────────────────────
    st.markdown(f"""
    <div class="monthly-totals">
        <div class="monthly-total">
            <div class="monthly-total-val">{card['total_views']:,}</div>
            <div class="monthly-total-label">Total Views</div>
        </div>
        <div class="monthly-total">
            <div class="monthly-total-val">{card['total_saves']:,}</div>
            <div class="monthly-total-label">Total Saves</div>
        </div>
        <div class="monthly-total">
            <div class="monthly-total-val">{card['total_likes']:,}</div>
            <div class="monthly-total-label">Total Likes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MoM METRIC GRID ───────────────────────────
    vc_cls, vc_txt = _change_class(card.get("view_change"))
    rc_cls, rc_txt = _change_class(card.get("ret_change"))
    ec_cls, ec_txt = _change_class(card.get("eng_change"))
    sc_cls, sc_txt = _change_class(card.get("save_change"))

    st.markdown(f"""
    <div class="monthly-metrics">
        <div class="monthly-metric">
            <div class="monthly-metric-label">Avg Views</div>
            <div class="monthly-metric-val">{card['avg_views']:,}</div>
            <div class="monthly-metric-change {vc_cls}">{vc_txt}</div>
        </div>
        <div class="monthly-metric">
            <div class="monthly-metric-label">Avg Retention</div>
            <div class="monthly-metric-val">{card['avg_retention']}%</div>
            <div class="monthly-metric-change {rc_cls}">{rc_txt}</div>
        </div>
        <div class="monthly-metric">
            <div class="monthly-metric-label">Avg Engagement</div>
            <div class="monthly-metric-val">{card['avg_engagement']}%</div>
            <div class="monthly-metric-change {ec_cls}">{ec_txt}</div>
        </div>
        <div class="monthly-metric">
            <div class="monthly-metric-label">Avg Save Rate</div>
            <div class="monthly-metric-val">{card['avg_save_rate']}%</div>
            <div class="monthly-metric-change {sc_cls}">{sc_txt}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── MOST IMPROVED ─────────────────────────────
    if card.get("most_improved") and card.get("most_improved_val", 0) > 0:
        st.markdown(
            f'<div class="monthly-improved">'
            f'🏅 Most Improved: {card["most_improved"]} +{card["most_improved_val"]:.0f}%'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── CATEGORY BREAKDOWN ────────────────────────
    breakdown = card.get("category_breakdown", [])
    if breakdown:
        st.markdown('<div class="section-label" style="margin-top:1.6rem;">Content Breakdown</div>', unsafe_allow_html=True)
        max_views = breakdown[0]["avg_views"] if breakdown else 1
        rows_html = ""
        for row in breakdown:
            bar_pct = round((row["avg_views"] / max_views) * 100) if max_views else 0
            rows_html += (
                f'<div class="monthly-cat-row">'
                f'<span class="monthly-cat-name">{row["category"]}</span>'
                f'<div class="monthly-cat-bar-track">'
                f'<div class="monthly-cat-bar-fill" style="width:{bar_pct}%"></div>'
                f'</div>'
                f'<span class="monthly-cat-views">{row["avg_views"]:,} avg views</span>'
                f'</div>'
            )
        st.markdown(f'<div style="margin-top:0.5rem;">{rows_html}</div>', unsafe_allow_html=True)

    # ── BEST REEL ─────────────────────────────────
    best = card.get("best_reel")
    if best:
        st.markdown('<div class="section-label" style="margin-top:1.6rem;">Best Reel This Month</div>', unsafe_allow_html=True)
        b_cap   = (best.get("caption") or best.get("category") or "Untitled")[:90]
        b_views = f'{best.get("views", 0):,}'
        b_ret   = f'{(best.get("retention_ratio") or 0) * 100:.0f}%'
        b_eng   = f'{(best.get("engagement_rate") or 0) * 100:.1f}%'
        b_saves = best.get("saves", 0)
        best_body = (
            f'<div style="font-size:0.64rem;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;'
            f'color:#00E5A0;margin-bottom:0.6rem;">🏆 Top Performer</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:rgba(255,255,255,0.85);'
            f'line-height:1.5;margin-bottom:0.75rem;">"{b_cap}"</div>'
            f'<div style="font-size:0.78rem;color:#888888;">'
            f'{b_views} views · {b_ret} retention · {b_eng} engagement · {b_saves:,} saves</div>'
        )
        st.markdown(theme_engine.rio_card("Best Reel This Month", best_body, "success"), unsafe_allow_html=True)

    # ── REFRESH ───────────────────────────────────
    st.markdown("<div style='margin-top:1.35rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button("🔄 Regenerate", key="monthly_regen_btn"):
        st.session_state["monthly_data"] = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# PHASE 8 — BENCHMARK COMPARISON
# ─────────────────────────────────────────────────

def _bench_ring_html(score: int, colour_class: str) -> str:
    """SVG score ring for benchmark tab."""
    COLOUR_MAP = {
        "crushing": "#00E5A0",
        "above":    "#7DFFCC",
        "on_par":   "#FFB020",
        "below":    "#FF8C00",
        "lagging":  "#FF3D71",
    }
    colour = COLOUR_MAP.get(colour_class, "#FFB020")
    r, cx, cy, stroke = 48, 60, 60, 10
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100)
    return f"""
    <div class="bench-score-wrap">
        <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
                stroke="rgba(255,255,255,0.06)" stroke-width="{stroke}"/>
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none"
                stroke="{colour}" stroke-width="{stroke}"
                stroke-dasharray="{circumference:.1f}"
                stroke-dashoffset="{offset:.1f}"
                stroke-linecap="square"
                transform="rotate(-90 {cx} {cy})"/>
            <text x="{cx}" y="{cy - 4}" text-anchor="middle"
                font-family="Syne,sans-serif" font-size="22" font-weight="800"
                fill="{colour}">{score}</text>
            <text x="{cx}" y="{cy + 14}" text-anchor="middle"
                font-family="Inter,sans-serif" font-size="9" font-weight="700"
                fill="rgba(255,255,255,0.38)" letter-spacing="1.5">/100</text>
        </svg>
    </div>"""


def _grade_chip(grade: str, cls: str) -> str:
    return f'<span class="bench-grade-{cls}" style="font-size:0.72rem;font-weight:700;">{grade}</span>'


def render_competitor_benchmarks():
    st.markdown("""
    <div class="bench-hero">
        <div class="bench-hero-title">Industry Benchmark Report</div>
        <div class="bench-hero-sub">See exactly how your reels stack up against creators
        at your follower level — views, retention, engagement, save rate.</div>
    </div>
    """, unsafe_allow_html=True)

    uid = st.session_state.get("user_id")
    atk = st.session_state.get("access_token")
    rtk = st.session_state.get("refresh_token")

    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    generate = st.button("📊 Generate Benchmark Report", use_container_width=True, key="bench_gen_btn")
    st.markdown('</div>', unsafe_allow_html=True)

    if generate:
        with st.spinner("Comparing your reels to industry benchmarks…"):
            reels, err = get_user_reels(uid, atk, rtk)
        if err or not reels:
            st.error("Could not load your reels. Save at least one reel first.")
            return
        report = compute_benchmark_report(reels)
        st.session_state["benchmark_data"] = report
        st.rerun()

    report = st.session_state.get("benchmark_data")
    if not report:
        st.markdown(
            '<p style="font-size:0.78rem;color:rgba(255,255,255,0.22);text-align:center;'
            'margin-top:2rem;">Hit Generate to compare your metrics against industry averages.</p>',
            unsafe_allow_html=True,
        )
        return

    if not report.get("has_data"):
        st.warning("No reels found. Analyse and save at least one reel first.")
        return

    # ── Tier badge ────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="bench-tier-badge">🎯 {report["tier_label"]} · '
        f'{report["reel_count"]} reels analysed · '
        f'Benchmarked vs {report["primary_category"]}</div>',
        unsafe_allow_html=True,
    )

    # ── Score ring ────────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Benchmark Score</div>', unsafe_allow_html=True)
    ring_html = _bench_ring_html(report["benchmark_score"], report["score_colour"])
    st.markdown(ring_html, unsafe_allow_html=True)
    lbl_colour = {
        "crushing": "#00E5A0", "above": "#7DFFCC",
        "on_par": "#FFB020",   "below": "#FF8C00", "lagging": "#FF3D71",
    }.get(report["score_colour"], "#FFB020")
    st.markdown(
        f'<div class="bench-score-label" style="text-align:center;color:{lbl_colour};">'
        f'{report["score_label"]}</div>',
        unsafe_allow_html=True,
    )

    # ── Strongest metric chip ─────────────────────────────────────────────
    sign = "+" if report["strongest_delta"] >= 0 else ""
    st.markdown(
        f'<div style="text-align:center;">'
        f'<div class="bench-strongest">✨ Strongest: {report["strongest_metric"]} '
        f'— {sign}{report["strongest_delta"]}% vs benchmark</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 4-metric comparison grid ──────────────────────────────────────────
    st.markdown('<div class="section-label" style="margin-top:1.4rem;">Your Metrics vs Industry</div>', unsafe_allow_html=True)

    metrics = [
        ("👁 Views",       report["user_avg_views"],       report["bench_avg_views"],
         f'{report["user_avg_views"]:,}',                  f'{report["bench_avg_views"]:,}',
         report["delta_views"],  report["grade_views"],    report["cls_views"]),
        ("⏱ Retention",    report["user_avg_retention"],   report["bench_avg_retention"],
         f'{report["user_avg_retention"]}%',               f'{report["bench_avg_retention"]}%',
         report["delta_ret"],    report["grade_ret"],      report["cls_ret"]),
        ("❤️ Engagement",  report["user_avg_engagement"],  report["bench_avg_engagement"],
         f'{report["user_avg_engagement"]}%',              f'{report["bench_avg_engagement"]}%',
         report["delta_eng"],    report["grade_eng"],      report["cls_eng"]),
        ("🔖 Save Rate",   report["user_avg_save_rate"],   report["bench_avg_save_rate"],
         f'{report["user_avg_save_rate"]}%',               f'{report["bench_avg_save_rate"]}%',
         report["delta_save"],   report["grade_save"],     report["cls_save"]),
    ]

    cards_html = '<div class="bench-grid">'
    for label, _uv, _bv, user_fmt, bench_fmt, delta, grade, cls in metrics:
        sign = "+" if delta >= 0 else ""
        delta_colour = {
            "crushing": "#00E5A0", "above": "#7DFFCC",
            "on_par": "#FFB020",   "below": "#FF8C00", "lagging": "#FF3D71",
        }.get(cls, "#FFB020")
        cards_html += f"""
        <div class="bench-metric-card">
            <div class="bench-metric-title">{label}</div>
            <div class="bench-metric-row">
                <span class="bench-metric-user">{user_fmt}</span>
                <span class="bench-metric-vs">you</span>
            </div>
            <div class="bench-metric-row" style="margin-top:0.2rem;">
                <span class="bench-metric-industry">{bench_fmt}</span>
                <span class="bench-metric-vs">industry</span>
            </div>
            <div class="bench-metric-delta" style="color:{delta_colour};">
                {sign}{delta}% · {grade}
            </div>
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Biggest opportunities ──────────────────────────────────────────────
    opps = report.get("opportunity_cards", [])
    if opps:
        st.markdown('<div class="section-label" style="margin-top:1.4rem;">Biggest Opportunities</div>', unsafe_allow_html=True)
        opp_html = '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;">'
        for opp in opps:
            opp_sign = "+" if opp["delta_pct"] >= 0 else ""
            card_body = (
                f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.10em;text-transform:uppercase;color:#FCB045;margin-bottom:0.5rem;">📈 {opp["metric"]}</div>'
                f'<div style="font-size:1.5rem;font-weight:800;color:rgba(255,255,255,0.85);margin-bottom:0.3rem;">{opp["user_val"]} '
                f'<span style="font-size:0.72rem;color:rgba(255,255,255,0.35);">you</span></div>'
                f'<div style="font-size:0.78rem;color:#888888;margin-bottom:0.5rem;">Industry avg: {opp["bench_val"]} ({opp_sign}{opp["delta_pct"]}%)</div>'
                f'<div style="font-size:0.80rem;color:rgba(255,255,255,0.65);font-weight:600;">🎯 Target: {opp["target"]}</div>'
            )
            opp_html += theme_engine.rio_card("Opportunity", card_body, "alert")
        opp_html += '</div>'
        st.markdown(opp_html, unsafe_allow_html=True)

    # ── Category breakdown table ───────────────────────────────────────────
    cats = report.get("category_breakdown", [])
    if cats:
        st.markdown('<div class="section-label" style="margin-top:1.4rem;">Performance by Category</div>', unsafe_allow_html=True)
        table_html = """
        <div class="bench-cat-table">
            <div class="bench-cat-header">
                <span>Category</span>
                <span>Your Views</span>
                <span>Benchmark</span>
                <span>Grade</span>
            </div>"""
        for row in cats:
            delta_sign = "+" if row["delta_views"] >= 0 else ""
            grade_colour = {
                "crushing": "#00E5A0", "above": "#7DFFCC",
                "on_par": "#FFB020",   "below": "#FF8C00", "lagging": "#FF3D71",
            }.get(row["cls_views"], "#FFB020")
            table_html += f"""
            <div class="bench-cat-row">
                <span class="bench-cat-name">{row["category"]} <span style="font-size:0.60rem;color:rgba(255,255,255,0.30);">({row["count"]})</span></span>
                <span class="bench-cat-val">{row["avg_views"]:,}</span>
                <span class="bench-cat-val">{row["bench_views"]:,}</span>
                <span style="font-size:0.72rem;font-weight:700;color:{grade_colour};">{delta_sign}{row["delta_views"]}%</span>
            </div>"""
        table_html += '</div>'
        st.markdown(table_html, unsafe_allow_html=True)

    # ── Refresh ────────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button("🔄 Refresh Report", key="bench_refresh_btn"):
        st.session_state["benchmark_data"] = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────
def render_main_app():
    email_display = st.session_state.user_email or ""
    nav_col, logout_col = st.columns([5, 1])
    with nav_col:
        st.markdown(
            '<div class="nav-wrap">'
            + theme_engine.get_logo_html(font_size="1.35rem")
            + f'<span class="nav-user">{email_display}</span>'
            + '</div>',
            unsafe_allow_html=True,
        )
    with logout_col:
        st.markdown("<div style='padding-top:1.35rem;'><div class='ghost-btn'>", unsafe_allow_html=True)
        if st.button("Log Out", key="logout_btn"):
            for k in ["authenticated", "user_id", "user_email",
                      "access_token", "refresh_token", "save_status", "save_error_msg",
                      "patterns_data", "patterns_insights", "patterns_roadmap"]:
                st.session_state[k] = False if k == "authenticated" else (
                    "" if k == "save_error_msg" else None
                )
            st.session_state.patterns_loaded = False
            st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="nav-separator"></div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="hero">
        <div class="badge">⚡ AI Content Intelligence</div>
        <p class="hero-sub">Understand exactly why your Instagram Reels performed the way they did.<br>
        Specific, plain-language diagnostics built for solo creators.</p>
    </div>
    """, unsafe_allow_html=True)

    single_tab, csv_tab, patterns_tab, prescore_tab, brief_tab, digest_tab, monthly_tab, bench_tab = st.tabs([
        "⚡ Analyse",
        "📊 Import",
        "📈 Patterns",
        "🎯 Pre-Score",
        "📝 Brief",
        "📧 Digest",
        "🗓 Monthly",
        "🏆 Benchmark",
    ])

    with single_tab:
        render_single_reel()

    with csv_tab:
        render_csv_import()

    with patterns_tab:
        render_patterns()

    with prescore_tab:
        render_pre_score()

    with brief_tab:
        render_content_brief()

    with digest_tab:
        render_weekly_digest()

    with monthly_tab:
        render_monthly_card()

    with bench_tab:
        render_competitor_benchmarks()


# ─────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────
inject_css()

if st.session_state.authenticated:
    render_main_app()
else:
    render_auth_page()
