"""
theme_engine.py  ·  Reel IQ Design System
──────────────────────────────────────────
Single source of truth for all visual tokens, typography, and the
CSS design system. Import and call inject_design_system() in app.py.

Design Tokens
─────────────
Background  #050505   (pure black depth)
Card        #111111   with 1px border rgba(255,255,255,0.08)
Primary     #FFFFFF
Secondary   #888888
Muted       rgba(255,255,255,0.28)
Gradient    #833AB4 → #E1306C → #FCB045  (Instagram gradient)
Font        Inter (all weights, globally forced)
Header LS   -0.02em
"""

from __future__ import annotations
import streamlit as st

# ──────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ──────────────────────────────────────────────────────────────
TOKENS = {
    "bg":           "#050505",
    "card":         "#111111",
    "card_deep":    "#0D0D0D",
    "border":       "rgba(255,255,255,0.08)",
    "border_light": "rgba(255,255,255,0.05)",
    "text_primary": "#FFFFFF",
    "text_secondary": "#888888",
    "text_muted":   "rgba(255,255,255,0.28)",

    # Instagram gradient
    "grad":         "linear-gradient(90deg, #833AB4 0%, #E1306C 50%, #FCB045 100%)",
    "grad_start":   "#833AB4",
    "grad_mid":     "#E1306C",
    "grad_end":     "#FCB045",

    # Status / semantic
    "good":     "#00E5A0",
    "average":  "#FFB020",
    "poor":     "#FF3D71",

    # Font
    "font":     "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
}


# ──────────────────────────────────────────────────────────────
# LOGO  —  SVG wordmark
# ──────────────────────────────────────────────────────────────

def get_logo_html(font_size: str = "1.45rem", tagline: bool = False) -> str:
    """
    Returns HTML for the 'Reel IQ' gradient wordmark.
    'Reel' — Inter 400, 'IQ' — Inter 800, both in Instagram gradient.
    """
    grad = "linear-gradient(90deg, #833AB4 0%, #E1306C 50%, #FCB045 100%)"
    tagline_html = (
        '<div style="font-size:0.46rem;font-weight:700;letter-spacing:0.36em;'
        'text-transform:uppercase;color:rgba(255,255,255,0.16);margin-top:0.25rem;'
        'font-family:Inter,sans-serif;-webkit-text-fill-color:rgba(255,255,255,0.16);">'
        'Content Intelligence</div>'
    ) if tagline else ""

    return (
        f'<span style="display:inline-block;background:{grad};'
        f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        f'background-clip:text;font-family:Inter,-apple-system,sans-serif;'
        f'font-size:{font_size};letter-spacing:-0.02em;line-height:1;">'
        f'<span style="font-weight:300;">Reel</span>'
        f'<span style="font-weight:800;">&nbsp;IQ</span>'
        f'</span>'
        + tagline_html
    )


# ──────────────────────────────────────────────────────────────
# RIO CARD  —  unified content card component
# ──────────────────────────────────────────────────────────────

def rio_card(title: str, content: str, color_type: str = "default") -> str:
    """
    Returns an HTML string for a unified content card.

    Args:
        title:      Optional header label (empty string = no header bar).
        content:    Raw HTML for the card body.
        color_type: "default" | "success" | "alert"
                    - default → Instagram gradient top accent, no glow
                    - success → green top accent + subtle green glow
                    - alert   → orange top accent + subtle orange glow
    """
    if color_type == "success":
        accent = "linear-gradient(90deg, #00B37A 0%, #00E5A0 100%)"
        glow   = "box-shadow:0 0 0 1px rgba(0,229,160,0.12),0 4px 24px rgba(0,229,160,0.06);"
    elif color_type == "alert":
        accent = "linear-gradient(90deg, #CC8800 0%, #FCB045 100%)"
        glow   = "box-shadow:0 0 0 1px rgba(252,176,69,0.12),0 4px 24px rgba(252,176,69,0.06);"
    else:
        accent = "linear-gradient(90deg, #833AB4 0%, #E1306C 50%, #FCB045 100%)"
        glow   = ""

    header_html = (
        f'<div class="rio-card-title">{title}</div>'
        if title else ""
    )

    return (
        f'<div class="rio-card" style="{glow}">'
        f'<div class="rio-card-accent" style="background:{accent};"></div>'
        + header_html +
        f'<div class="rio-card-body">{content}</div>'
        f'</div>'
    )


# ──────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call in app.py)
# ──────────────────────────────────────────────────────────────

def set_page_config():
    """
    Call this as the FIRST Streamlit operation in app.py.
    Replaces the raw st.set_page_config() call.
    """
    st.set_page_config(
        page_title="Reel IQ — Content Intelligence",
        page_icon="⚡",
        layout="centered",
        initial_sidebar_state="collapsed",
    )


# ──────────────────────────────────────────────────────────────
# DESIGN SYSTEM  CSS
# ──────────────────────────────────────────────────────────────

def inject_design_system():
    """
    Inject the complete Reel IQ design system CSS.
    Call once inside inject_css() in app.py BEFORE feature-specific styles.
    """
    st.markdown("""
<style>
/* ──────────────────────────────────────────────────────
   GOOGLE FONTS  —  Inter only (all weights 300–900)
────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ──────────────────────────────────────────────────────
   DESIGN TOKENS  (CSS custom properties)
────────────────────────────────────────────────────── */
:root {
    --bg:           #050505;
    --card:         #111111;
    --card-deep:    #0D0D0D;
    --border:       rgba(255,255,255,0.08);
    --border-light: rgba(255,255,255,0.05);
    --text-primary: #FFFFFF;
    --text-secondary: #888888;
    --text-muted:   rgba(255,255,255,0.28);
    --grad:         linear-gradient(90deg, #833AB4 0%, #E1306C 50%, #FCB045 100%);
    --grad-start:   #833AB4;
    --grad-mid:     #E1306C;
    --grad-end:     #FCB045;
    --good:         #00E5A0;
    --average:      #FFB020;
    --poor:         #FF3D71;
    --font:         'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --radius:       0px;
}

/* ──────────────────────────────────────────────────────
   GLOBAL RESET + TYPOGRAPHY
────────────────────────────────────────────────────── */
html, body, [class*="css"], * {
    font-family: var(--font) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text-primary) !important;
}
* { box-sizing: border-box; }

/* Typography hierarchy */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: var(--font) !important;
    letter-spacing: -0.02em !important;
    color: var(--text-primary) !important;
    font-weight: 800 !important;
}
p, li, span, div {
    font-family: var(--font) !important;
}

/* ──────────────────────────────────────────────────────
   HIDE STREAMLIT CHROME
────────────────────────────────────────────────────── */
#MainMenu           { visibility: hidden !important; }
footer              { visibility: hidden !important; }
header              { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.viewerBadge_container__1QSob { display: none !important; }

.block-container {
    padding-top: 0 !important;
    padding-bottom: 5rem !important;
    max-width: 880px !important;
}

/* Hide heading anchor links */
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a,
[data-testid="stMarkdownContainer"] h1 a,
[data-testid="stMarkdownContainer"] h2 a { display: none !important; }

/* ──────────────────────────────────────────────────────
   SCROLLBAR
────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.20); }

/* ──────────────────────────────────────────────────────
   TABS
────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 0 !important; padding: 3px !important;
    gap: 1px !important; border-bottom: none !important;
    overflow-x: auto !important; flex-wrap: nowrap !important;
    scrollbar-width: none !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border-radius: 0 !important;
    color: var(--text-secondary) !important; font-weight: 600 !important;
    font-size: 0.68rem !important; border: none !important;
    padding: 0.52rem 0.9rem !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    transition: color 0.18s !important;
    font-family: var(--font) !important;
    white-space: nowrap !important; flex-shrink: 0 !important;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.05) !important;
    color: var(--text-primary) !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] {
    background: transparent !important; padding-top: 1.5rem !important;
}

/* ──────────────────────────────────────────────────────
   INPUTS
────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--card-deep) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    font-family: var(--font) !important;
    font-size: 0.9rem !important; font-weight: 400 !important;
    padding: 0.72rem 1rem !important;
    transition: border-color 0.18s !important;
    caret-color: var(--grad-start) !important;
    letter-spacing: 0 !important;
}
.stTextInput > div > div > input:-webkit-autofill,
.stTextInput > div > div > input:-webkit-autofill:hover,
.stTextInput > div > div > input:-webkit-autofill:focus,
.stTextInput > div > div > input:-webkit-autofill:active,
.stNumberInput > div > div > input:-webkit-autofill,
.stNumberInput > div > div > input:-webkit-autofill:hover,
.stNumberInput > div > div > input:-webkit-autofill:focus {
    -webkit-box-shadow: 0 0 0 1000px var(--card-deep) inset !important;
    box-shadow: 0 0 0 1000px var(--card-deep) inset !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    border-color: var(--border) !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: rgba(131,58,180,0.50) !important;
    box-shadow: 0 0 0 2px rgba(131,58,180,0.08) !important;
    outline: none !important;
}
.stTextArea > div > div > textarea {
    background: var(--card-deep) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    font-family: var(--font) !important; font-size: 0.9rem !important;
    caret-color: var(--grad-start) !important; padding: 0.75rem 1rem !important;
    letter-spacing: 0 !important;
}
.stTextArea > div > div > textarea:focus {
    border-color: rgba(131,58,180,0.50) !important;
    box-shadow: 0 0 0 2px rgba(131,58,180,0.08) !important;
}
[data-baseweb="select"] > div {
    background: var(--card-deep) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important; color: var(--text-primary) !important;
}
[data-baseweb="popover"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}
[data-baseweb="menu"] { background: var(--card) !important; }
[data-baseweb="option"] { background: var(--card) !important; color: var(--text-primary) !important; }
[data-baseweb="option"]:hover { background: rgba(131,58,180,0.12) !important; }
label, .stTextInput label, .stNumberInput label, .stTextArea label, .stSelectbox label {
    color: var(--text-secondary) !important;
    font-size: 0.64rem !important; font-weight: 600 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    margin-bottom: 0.3rem !important;
    font-family: var(--font) !important;
}
.stCheckbox { margin: 0.25rem 0 0.5rem !important; }
.stCheckbox label {
    color: var(--text-secondary) !important;
    font-size: 0.64rem !important; font-weight: 500 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
}
.stCheckbox label:hover { color: var(--text-primary) !important; }
[data-testid="stCheckbox"] > label > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}
[data-testid="stCheckbox"] > label > div[data-checked="true"],
[data-testid="stCheckbox"] > label > div[aria-checked="true"] {
    background: var(--grad) !important;
    border-color: transparent !important;
}

/* ──────────────────────────────────────────────────────
   BUTTONS
────────────────────────────────────────────────────── */
.stButton > button {
    background: var(--grad) !important;
    color: var(--text-primary) !important; border: none !important;
    border-radius: 12px !important;
    font-family: var(--font) !important;
    font-weight: 700 !important; font-size: 0.78rem !important;
    height: 3rem !important;
    letter-spacing: 0.10em !important; text-transform: uppercase !important;
    box-shadow: 0 4px 24px rgba(131,58,180,0.22) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    box-shadow: 0 8px 36px rgba(131,58,180,0.36) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; opacity: 1 !important; }
.stDownloadButton > button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
    font-family: var(--font) !important;
    font-size: 0.72rem !important; height: 2.85rem !important;
    font-weight: 600 !important; letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    box-shadow: none !important; transition: all 0.18s !important;
}
.stDownloadButton > button:hover {
    border-color: rgba(255,255,255,0.28) !important;
    color: var(--text-primary) !important;
    transform: none !important;
}
/* Ghost button — secondary actions */
div.ghost-btn > div > button, div.ghost-btn button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: var(--font) !important;
    font-size: 0.68rem !important; height: 2.2rem !important;
    font-weight: 500 !important; letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    box-shadow: none !important; padding: 0 1rem !important;
    min-width: 0 !important; width: auto !important;
    transition: all 0.18s !important;
}
div.ghost-btn > div > button:hover, div.ghost-btn button:hover {
    background: rgba(255,255,255,0.04) !important;
    color: var(--text-primary) !important;
    border-color: rgba(255,255,255,0.18) !important;
    transform: none !important; box-shadow: none !important;
}

/* ──────────────────────────────────────────────────────
   NAVBAR
────────────────────────────────────────────────────── */
.nav-wrap {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.4rem 0 1.1rem;
}
.nav-user {
    font-size: 0.72rem; color: var(--text-secondary);
    font-weight: 400; letter-spacing: 0;
}
.nav-separator {
    height: 1px; margin-bottom: 2rem;
    background: linear-gradient(90deg,
        rgba(131,58,180,0.28) 0%,
        rgba(225,48,108,0.14) 45%,
        transparent 80%);
}

/* ──────────────────────────────────────────────────────
   AUTH PAGE
────────────────────────────────────────────────────── */
.auth-ambient {
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none; z-index: 0;
    background:
        radial-gradient(ellipse 60% 50% at 20% 0%,  rgba(131,58,180,0.10) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 80% 100%, rgba(252,176,69,0.07) 0%, transparent 55%);
}
.auth-brand { text-align: center; padding: 3rem 0 1.75rem; }
.auth-logo-row {
    display: inline-flex; align-items: center; justify-content: center;
    margin-bottom: 0.65rem;
}
.auth-tagline {
    display: block;
    font-size: 0.54rem; font-weight: 700; letter-spacing: 0.32em;
    color: rgba(255,255,255,0.15); text-transform: uppercase;
    margin-top: 0.35rem;
}
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0 !important; -webkit-border-radius: 0 !important;
    box-shadow: 0 24px 64px rgba(0,0,0,0.72), 0 0 0 1px rgba(131,58,180,0.04) !important;
    overflow: hidden !important;
}
[data-testid="stVerticalBlockBorderWrapper"]::before {
    content: ''; display: block; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(131,58,180,0.55), rgba(225,48,108,0.30), rgba(252,176,69,0.22), transparent);
}
.forgot-panel-header { padding: 0.5rem 0 1.35rem; text-align: center; }
.forgot-panel-title {
    font-family: var(--font); font-size: 1.15rem; font-weight: 800;
    color: var(--text-primary); margin-bottom: 0.5rem; letter-spacing: -0.02em;
}
.forgot-panel-sub { font-size: 0.80rem; color: var(--text-secondary); line-height: 1.65; }
.forgot-link-btn button, .forgot-link-btn > div > button {
    background: transparent !important;
    color: rgba(131,58,180,0.75) !important;
    border: none !important; box-shadow: none !important;
    font-size: 0.62rem !important; font-weight: 700 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    height: 1.8rem !important; padding: 0 0.1rem !important;
    min-height: 0 !important; line-height: 1 !important;
}
.forgot-link-btn button:hover, .forgot-link-btn > div > button:hover {
    color: #833AB4 !important; background: transparent !important; box-shadow: none !important;
}
.auth-footer {
    text-align: center; margin-top: 1.5rem; padding-top: 1.4rem;
    border-top: 1px solid var(--border-light);
}
.auth-footer p { font-size: 0.68rem; color: rgba(255,255,255,0.16); font-weight: 400; line-height: 1.65; margin: 0; }
@media (max-width: 640px) {
    .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; }
}

/* ──────────────────────────────────────────────────────
   HERO SECTION
────────────────────────────────────────────────────── */
.hero { text-align: center; padding: 0.8rem 1rem 1rem; position: relative; }
.hero::before {
    content: ''; position: absolute; top: -10px; left: 50%; transform: translateX(-50%);
    width: 560px; height: 280px;
    background: radial-gradient(ellipse,
        rgba(131,58,180,0.05) 0%, rgba(225,48,108,0.03) 40%, transparent 70%);
    pointer-events: none;
}
.badge {
    display: inline-flex; align-items: center; gap: 0.45rem;
    background: rgba(131,58,180,0.07); border: 1px solid rgba(131,58,180,0.20);
    color: rgba(170,100,220,0.90); font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.22em; text-transform: uppercase;
    padding: 0.3rem 1.15rem; border-radius: 0; margin-bottom: 0.9rem;
}
.hero-sub {
    font-size: 1.1rem; font-weight: 400; color: #888888;
    line-height: 1.65; max-width: 700px; margin: 0 auto;
}
@media (max-width: 640px) { .hero-title { font-size: 2.3rem; } }

/* ──────────────────────────────────────────────────────
   SECTION LABELS
────────────────────────────────────────────────────── */
.section-label {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.22em;
    text-transform: uppercase; color: rgba(131,58,180,0.70);
    margin: 2.25rem 0 1.1rem;
    display: flex; align-items: center; gap: 1rem;
}
.section-label::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(to right, rgba(131,58,180,0.15), transparent);
}

/* ──────────────────────────────────────────────────────
   SCORE GRID
────────────────────────────────────────────────────── */
.score-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1px; margin: 1.5rem 0;
    background: var(--border);
    border: 1px solid var(--border);
}
@media (max-width: 640px) { .score-grid { grid-template-columns: repeat(2, 1fr); } }
.score-card {
    background: var(--card); padding: 1.75rem 1rem 1.5rem;
    text-align: center; position: relative; overflow: hidden;
    transition: background 0.18s;
}
.score-card:hover { background: #181818; }
.score-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
}
.score-card.good::before   { background: linear-gradient(90deg, #00B37A, #00E5A0); }
.score-card.average::before { background: linear-gradient(90deg, #CC8800, #FFB020); }
.score-card.poor::before   { background: linear-gradient(90deg, #CC1A3A, #FF3D71); }
.score-label {
    font-size: 0.54rem; font-weight: 700; letter-spacing: 0.20em;
    text-transform: uppercase; color: var(--text-muted);
    margin-bottom: 0.9rem;
}
.score-value {
    font-size: 2.75rem; font-weight: 800; line-height: 1;
    margin-bottom: 0.7rem; display: block; letter-spacing: -0.02em;
}
.score-card.good .score-value   { color: var(--good); }
.score-card.average .score-value { color: var(--average); }
.score-card.poor .score-value   { color: var(--poor); }
.score-tag {
    display: inline-block; font-size: 0.56rem; font-weight: 700;
    padding: 0.22rem 0.8rem; border-radius: 0;
    letter-spacing: 0.10em; text-transform: uppercase;
}
.score-card.good .score-tag   { background: rgba(0,229,160,0.10);  color: var(--good);    border: 1px solid rgba(0,229,160,0.20); }
.score-card.average .score-tag { background: rgba(255,176,32,0.10); color: var(--average); border: 1px solid rgba(255,176,32,0.20); }
.score-card.poor .score-tag   { background: rgba(255,61,113,0.10);  color: var(--poor);   border: 1px solid rgba(255,61,113,0.20); }

/* ──────────────────────────────────────────────────────
   INSIGHT BLOCKS
────────────────────────────────────────────────────── */
.insight-block {
    background: var(--card); border: 1px solid var(--border-light);
    border-radius: 0; padding: 1.2rem 1.4rem 1.2rem 1.5rem;
    margin-bottom: 2px; position: relative; transition: background 0.15s;
}
.insight-block:hover { background: #181818; }
.insight-block::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
}
.insight-block.good::before   { background: var(--good); }
.insight-block.average::before { background: var(--average); }
.insight-block.poor::before   { background: var(--poor); }
.insight-title {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; margin-bottom: 0.42rem; letter-spacing: -0.00em;
}
.insight-block.good .insight-title   { color: var(--good); }
.insight-block.average .insight-title { color: var(--average); }
.insight-block.poor .insight-title   { color: var(--poor); }
.insight-text { font-size: 0.875rem; color: var(--text-secondary); line-height: 1.75; font-weight: 400; }

/* ──────────────────────────────────────────────────────
   AI REPORT CARD
────────────────────────────────────────────────────── */
.report-container {
    background: var(--card); border: 1px solid var(--border);
    border-top: 2px solid;
    border-image: var(--grad) 1;
    padding: 1.85rem; margin-top: 1.35rem; position: relative;
}
.report-header {
    display: flex; align-items: center; gap: 0.9rem;
    margin-bottom: 1.4rem; padding-bottom: 1.1rem;
    border-bottom: 1px solid var(--border-light);
}
.report-dot {
    width: 8px; height: 8px; flex-shrink: 0;
    background: var(--grad);
    border-radius: 0; box-shadow: 0 0 10px rgba(131,58,180,0.50);
}
.report-title { font-size: 0.85rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.01em; }
.report-subtitle { font-size: 0.66rem; color: var(--text-secondary); font-weight: 400; margin-top: 0.12rem; }
.report-body { font-size: 0.875rem; color: var(--text-secondary); line-height: 1.95; font-weight: 400; white-space: pre-wrap; }

/* ──────────────────────────────────────────────────────
   SAVE / ERROR BADGES
────────────────────────────────────────────────────── */
.save-success {
    display: flex; align-items: center; gap: 0.7rem;
    background: rgba(0,229,160,0.05); border: 1px solid rgba(0,229,160,0.15);
    border-radius: 0; padding: 0.85rem 1.1rem;
    font-size: 0.80rem; color: var(--good); font-weight: 600; margin-top: 0.85rem;
}
.save-error {
    display: flex; align-items: center; gap: 0.7rem;
    background: rgba(255,61,113,0.05); border: 1px solid rgba(255,61,113,0.15);
    border-radius: 0; padding: 0.85rem 1.1rem;
    font-size: 0.80rem; color: var(--poor); font-weight: 600; margin-top: 0.85rem;
}

/* ──────────────────────────────────────────────────────
   LOADING
────────────────────────────────────────────────────── */
.loading-state { text-align: center; padding: 4rem 1rem; }
.loading-ring {
    width: 44px; height: 44px;
    border: 2px solid rgba(255,255,255,0.06);
    border-top: 2px solid #833AB4;
    border-radius: 50%; animation: spin 0.85s linear infinite; margin: 0 auto 1.4rem;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 0.88rem; color: var(--text-secondary); font-weight: 400; }
.loading-sub  { font-size: 0.74rem; color: var(--text-muted); margin-top: 0.32rem; }

/* ──────────────────────────────────────────────────────
   PROGRESS BAR
────────────────────────────────────────────────────── */
.stProgress > div > div { background: var(--grad) !important; border-radius: 0 !important; }
.stProgress > div { background: rgba(255,255,255,0.05) !important; border-radius: 0 !important; }

/* ──────────────────────────────────────────────────────
   FILE UPLOADER
────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.018) !important;
    border: 1px dashed rgba(131,58,180,0.28) !important;
    border-radius: 8px !important; transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: rgba(131,58,180,0.50) !important; }

/* ──────────────────────────────────────────────────────
   MISC
────────────────────────────────────────────────────── */
div[data-testid="stForm"] { background: transparent !important; border: none !important; padding: 0 !important; }
.stAlert { border-radius: 0 !important; }
.stSuccess { background: rgba(0,229,160,0.05) !important; border: 1px solid rgba(0,229,160,0.15) !important; color: var(--good) !important; border-radius: 0 !important; }
.stError   { background: rgba(255,61,113,0.05) !important; border: 1px solid rgba(255,61,113,0.15) !important; border-radius: 0 !important; }
hr { border-color: var(--border-light) !important; margin: 2rem 0 !important; }
.stNumberInput button { background: rgba(255,255,255,0.03) !important; border-color: var(--border) !important; color: var(--text-secondary) !important; }
[data-testid="stDataFrame"] { border-radius: 0 !important; overflow: hidden; }

/* ──────────────────────────────────────────────────────
   RIO CARD  —  unified content card system
────────────────────────────────────────────────────── */
.rio-card {
    background: #111111;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1rem;
    transition: box-shadow 0.2s;
}
.rio-card-accent {
    height: 2px;
    width: 100%;
}
.rio-card-title {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #888888;
    padding: 1rem 1.4rem 0.6rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-family: 'Inter', sans-serif;
}
.rio-card-body {
    padding: 1.2rem 1.4rem;
}
</style>
""", unsafe_allow_html=True)
