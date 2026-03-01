# Reel IQ — Product Requirements Document

**Version:** 1.0 (Post-Build)
**Status:** All 8 phases complete
**Capstone:** AILP Capstone 2026 — AI-Based Content Performance Diagnostic System
**Live App:** https://thesoulofsuccess-instagram-diagnostic-app.streamlit.app

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Feature Audit — All 8 Phases](#4-feature-audit--all-8-phases)
5. [User Journey](#5-user-journey)
6. [Diagnostic Scoring Engine](#6-diagnostic-scoring-engine)
7. [Design System](#7-design-system)
8. [Data Privacy & Security](#8-data-privacy--security)
9. [Session State Reference](#9-session-state-reference)
10. [Module Reference](#10-module-reference)

---

## 1. Executive Summary

### Mission

Reel IQ is an AI-powered Instagram Reels performance diagnostic tool built specifically for **solo creators with fewer than 10,000 followers**. These creators produce content without access to expensive agency analytics, rarely understand why individual reels underperform, and have no reference point for what "good" looks like at their follower tier.

Reel IQ closes that gap. It ingests reel performance data — either entered manually or imported from Meta Business Suite — and returns:

- **Plain-language explanations** of why each metric scored as it did
- **Personalised benchmarks** built from the creator's own reel history
- **Pre-production scoring** so creators can optimise before they film
- **Industry comparisons** against 2025 Reels benchmarks segmented by follower tier and content category

### Target User

| Attribute | Profile |
|---|---|
| Follower count | 0 — 10,000 (nano) |
| Tech literacy | Moderate; comfortable with CSV exports |
| Pain point | Posts consistently but doesn't understand what's working or why |
| Goal | Grow reach and engagement without paying for a social media manager |

### Problem Statement

Most Instagram analytics dashboards (Meta Business Suite, Later, Sprout Social) show creators *what* happened — views fell, retention dropped. They do not explain *why* it happened or *what to do next*. For a solo creator without a marketing background, raw numbers are not actionable.

Reel IQ translates raw metrics into calibrated scores, benchmarked diagnoses, and GPT-generated plain-language recommendations — all inside a single self-serve web app, free of charge.

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **UI Framework** | Streamlit | Reactive Python web app; tab-based navigation; all rendering |
| **AI Engine** | OpenAI GPT-4o mini | Plain-language diagnostic reports, pre-score tips, content briefs, pattern insights |
| **Database & Auth** | Supabase (Postgres) | User authentication (sign-up / sign-in / password reset), reel storage, cross-session persistence |
| **Data Processing** | Pandas | CSV parsing, column detection, numeric normalisation |
| **Environment** | python-dotenv | Secure loading of `OPENAI_API_KEY` and `SUPABASE_*` variables from `.env` |
| **Design System** | Custom (`theme_engine.py`) | CSS tokens, logo, components — no third-party component library |
| **Hosting** | Streamlit Cloud | Serverless deployment; no Dockerfile required |

### Dependency Manifest (`requirements.txt`)

```
streamlit
python-dotenv
openai
supabase==2.0.3
pandas
```

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                        app.py                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │  Auth    │  │  8-Tab   │  │  render_*() functions  │ │
│  │  Page    │→ │  Layout  │→ │  (one per phase)       │ │
│  └──────────┘  └──────────┘  └───────────────────────┘ │
└───┬──────────────────────────────────────┬──────────────┘
    │                                      │
    ▼                                      ▼
┌──────────────────┐              ┌──────────────────────┐
│  Supabase        │              │  Business Logic       │
│  - Auth          │              │  - diagnostic_engine  │
│  - reel_analyses │              │  - pre_score_engine   │
│  (Postgres)      │              │  - patterns           │
└──────────────────┘              │  - email_digest       │
                                  │  - monthly_card       │
                                  │  - competitor         │
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │  OpenAI GPT-4o mini  │
                                  │  - ai_report         │
                                  │  - pre_score tips    │
                                  │  - content brief     │
                                  │  - pattern insights  │
                                  └──────────────────────┘
```

### Data Flow — Single Reel

```
User Input → run_diagnostic() → score dict → generate_ai_report() → display + save_reel_analysis()
```

### Data Flow — CSV Import

```
CSV Upload → build_column_map() → [row_to_inputs()] × N → run_diagnostic() × N → save_reel_analysis() × N
```

### Data Flow — Patterns / Benchmarks

```
get_user_reels() → compute_patterns() / compute_benchmark_report() → display + optional GPT call
```

---

## 4. Feature Audit — All 8 Phases

---

### Phase 1 — Single Reel Diagnostic (`render_single_reel`)

**Tab:** ⚡ Analyse

**Purpose:** Deep-dive diagnostic for a single already-published reel.

**Inputs**

| Field | Type | Notes |
|---|---|---|
| Views | Number | Primary reach metric |
| Total Watch Time (min) | Number | Used to calculate retention |
| Reel Duration (sec) | Number | Combined with watch time for retention ratio |
| Likes / Comments / Shares / Saves | Number | Engagement components |
| Follower Count | Number | Used for engagement tier benchmarking |
| Category | Select (15 options) | Maps to benchmark category |
| Hook Type | Select (9 options) | Qualitative input |
| Caption | Text | First line analysed for hook triggers |

**Processing**

1. `run_diagnostic(inputs)` → calculates four metric scores with explanations
2. `generate_ai_report(result, category)` → GPT-4o mini produces a full diagnostic narrative
3. `save_reel_analysis(user_id, inputs, result, report)` → persisted to Supabase

**Outputs**

- Section labels structure the page: `01 Reel Metrics`, `02 Content Details`, `03 Performance Scores`, `04 Score Breakdown`, `05 AI Diagnostic Report`
- **Score grid (4 cards):** Retention %, Engagement %, Hook Score /10, Save Rate % — each colour-coded good/average/poor
- **Score breakdown:** Four `insight-block` components per metric (severity-coded left border)
- **AI Report:** `rio_card("AI Analysis")` containing the full GPT narrative + model metadata
- Download button for full report as `.txt`

---

### Phase 2 — CSV Import (`render_csv_import`)

**Tab:** 📊 Import

**Purpose:** Bulk import of reel data from a Meta Business Suite CSV export.

**Inputs**

- CSV file (drag & drop or file picker)
- Follower count (single value applied to all rows)
- Category and Hook Type (applied batch-wide)

**Column Auto-Detection (`build_column_map`)**

The engine case-insensitively matches CSV headers against candidate lists:

| Internal Field | Accepted CSV Header Variants |
|---|---|
| `views` | Views, Video plays, Plays, Reel plays, Reach, Impressions |
| `likes` | Likes, Like count, Reactions |
| `comments` | Comments, Comment count |
| `shares` | Shares, Share count |
| `saves` | Saves, Save count, Bookmarks |
| `watch_time_minutes` | Total watch time (minutes), Watch time (minutes) |
| `reel_duration_seconds` | Duration (seconds), Video length |
| `caption` | Title, Description, Caption |
| `avg_watch_seconds` | Average watch time per play (seconds) |
| `avg_pct_watched` | Average percentage watched |

**Processing**

1. `safe_float()` sanitises all numeric fields (handles commas, NaN, empty strings)
2. `row_to_inputs()` builds a standardised input dict per row
3. Rows with 0 views are skipped automatically
4. Each valid row runs through `run_diagnostic()` then `save_reel_analysis()`
5. Progress bar updates per row

**Outputs**

- "How It Works" `rio_card` with step-by-step import instructions
- Detected columns list (before upload)
- Progress bar during processing
- "Import Summary" `rio_card` with success / skipped / failed counts

---

### Phase 3 — My Patterns (`render_patterns`)

**Tab:** 📈 Patterns

**Purpose:** Surface personal benchmarks and trends from the creator's reel history.

**Gate:** Minimum 5 reels required. Below threshold: shows current count and a progress indicator.

**Inputs**

- All saved reels fetched from Supabase via `get_user_reels(user_id)`

**Computed Metrics (`compute_patterns`)**

- Averages: Views, Retention %, Engagement %, Save Rate %
- Trend: % change between first half and second half of reel history (▲ / ▼ / →)
- Best hook type by avg retention
- Category breakdown: avg views per category

**Outputs**

- 4-card metric grid (avg values, colour-coded)
- Trend badge per metric (direction + magnitude vs earlier reels)
- "What your data is telling you" section:
  - **Generate AI Insights** button → `generate_ai_content(patterns)` via GPT-4o mini
  - AI insights text in `rio_card("AI Insights")`
  - Priority roadmap: action items ranked HIGH / MEDIUM / LOW
- Content type breakdown table (category × avg views)
- Refresh button to pull latest reel data

---

### Phase 4 — Pre-Score (`render_pre_score`)

**Tab:** 🎯 Pre-Score

**Purpose:** Predict performance score *before filming* — identify weaknesses in pre-production.

**Inputs**

| Field | Options |
|---|---|
| Planned Category | Educational, Inspirational, Transactional, Aesthetic, Entertainment |
| Hook Type | 9 options (same as Phase 1) |
| Planned Duration | 5 – 300 seconds |
| Follower Count | Numeric |
| Planned Caption Opening | Text (optional) |

**Scoring (`run_pre_score`)**

Four components × 25 points max = 100 total:

| Component | What it measures |
|---|---|
| Hook Strength | Hook type quality + caption triggers |
| Content Structure | Duration optimisation for category |
| Engagement Potential | Format + category engagement baseline |
| Audience Fit | Category/follower tier alignment |

Verdict thresholds: ≥ 70 → Strong · 40 – 69 → Moderate · < 40 → Needs Work

**Outputs**

- SVG ring visualisation (score 0 – 100, colour-coded)
- Verdict label + summary sentence
- Four horizontal component bars with labels and scores
- Risk flags (e.g., "Hook type rarely performs in this category")
- **Generate AI Tips** button → `generate_pre_score_tips(result)` → `rio_card("AI Recommendations")`
- Regenerate button

---

### Phase 5 — Content Brief (`render_content_brief`)

**Tab:** 📝 Brief

**Purpose:** Generate a production-ready content brief tailored to the creator's historical performance data.

**Inputs**

| Field | Notes |
|---|---|
| Reel Topic / Theme | Free text, e.g., "Morning routine for productivity" |
| Primary Goal | More Views, More Saves, More Engagement, Grow Followers, Drive Traffic, Sales |

**Personalisation Logic**

- If ≥ 5 reels in Supabase → personalised brief (includes best hook type, avg retention, top category)
- If < 5 reels → generic brief with a "log more reels" notice

**Processing (`generate_content_brief`)**

GPT-4o mini receives the topic, goal, and optionally: the creator's patterns data. Returns a structured brief with delimiter markers (`━━ FORMAT`, `━━ HOOK OPTIONS`, etc.).

`_parse_brief()` splits the raw response into labelled sections.

**Outputs inside `rio_card("Content Brief")`:**

| Section | Content |
|---|---|
| Meta | Model + goal + topic display |
| Format | Pill-style chips (Duration, Style, Editing) |
| Hook Options | 3 copyable hook lines |
| Caption Structure | Opening / Middle / CTA breakdown |
| Content Angle | Differentiated POV for this topic |
| Filming Notes | Camera angle, lighting, pacing tips |

Personalisation chip: `✓ Personalised from your data` or `⚠ Generic brief — log 5+ reels to personalise`

---

### Phase 6 — Weekly Digest (`render_weekly_digest`)

**Tab:** 📧 Digest

**Purpose:** Weekly performance snapshot delivered as a formatted email — or readable in-app.

**Data Source**

`build_digest_data(reels, email)` computes:

- Period: last 7 days of reels (or all-time if fewer)
- Metric averages with trend vs previous period
- Best reel and worst reel selection
- Best-performing category + recommended hook

**Outputs (in-app preview)**

- Period header
- 4-metric grid: Reel Count, Avg Views (+ trend), Avg Retention (+ trend), Total Saves
- Best reel card (`🏆`) with caption snippet and full stats
- Worst reel card (`⚠ Needs Attention`)
- `rio_card("Focus Tip", ..., "success")` — personalised tip based on best category
- **Send Digest** button → `send_digest_email()` → delivers HTML email to user's registered address
- Refresh button

---

### Phase 7 — Monthly Card (`render_monthly_card`)

**Tab:** 🗓 Monthly

**Purpose:** "Spotify Wrapped" style monthly summary — composite Growth Score with month-over-month comparison.

**Inputs**

- Month selector (current month back 11 months)

**Scoring (`compute_monthly_card`)**

Growth Score 0 – 100 composed from:
- Avg Views vs previous month
- Avg Retention vs previous month
- Avg Engagement vs previous month
- Avg Save Rate vs previous month

Verdict: Industry Leader (≥ 80), Above Average (≥ 60), On Par (≥ 40), Below Average (≥ 25), Needs Work (< 25)

**Outputs**

- SVG Growth Score ring with verdict label and "vs [prev month]" comparison
- Reel count + best hook type summary
- Totals grid: Total Views, Total Saves, Total Likes
- 4-metric MoM grid with directional arrows (▲ / ▼ / →) and % change
- `rio_card("Best Reel This Month", ..., "success")` — top performer with stats
- Regenerate button

---

### Phase 8 — Industry Benchmark Report (`render_competitor_benchmarks`)

**Tab:** 🏆 Benchmark

**Purpose:** Compare creator averages against 2025 industry benchmarks, segmented by follower tier and content category.

**Benchmark Data Structure**

20 benchmark sets: 5 categories × 4 follower tiers

| Tier | Follower Range |
|---|---|
| Nano | 0 – 10K |
| Micro | 10K – 50K |
| Mid | 50K – 200K |
| Macro | 200K+ |

Categories: Educational, Entertainment, Inspirational, Transactional, Aesthetic

Each set defines: `avg_views`, `avg_retention`, `avg_engagement`, `avg_save_rate`.

**Tier Detection**

Auto-detected from the **median follower count** across all saved reels.

**Grading Scale**

| Delta vs Benchmark | Grade | Colour |
|---|---|---|
| ≥ +30% | Crushing It | #00E5A0 |
| ≥ +10% | Above Avg | #7DFFCC |
| ≥ −10% | On Par | #FFB020 |
| ≥ −25% | Below Avg | #FF8C00 |
| < −25% | Lagging | #FF3D71 |

**Benchmark Score (0 – 100)**

25 points per metric. Scoring curve: at benchmark = 12.5 pts, +30% above = 25 pts, −40% below = 0 pts.

**Outputs**

- Tier badge: `🎯 Nano Tier · 12 reels analysed · Benchmarked vs Educational`
- Score ring with verdict + 4-component breakdown
- Overall metric comparison: user avg vs industry avg per metric with grade chip
- `rio_card("Opportunity", ..., "alert")` × 2 — lowest-delta metrics with specific targets
- Category breakdown table — per-category performance vs benchmarks
- Strongest metric chip (best-performing metric vs benchmark)

---

## 5. User Journey

### Full Flow Diagram

```
[Landing / Auth Page]
        │
        ├─ New user? → Sign Up → Supabase creates account → Main App
        └─ Returning? → Log In → Token validated → Main App

[Main App]
        │
        ├─ [Tab 1: ⚡ Analyse]
        │       Enter reel metrics manually
        │       → Score + AI diagnostic
        │       → Saved to Supabase
        │
        ├─ [Tab 2: 📊 Import]
        │       Upload Meta CSV
        │       → Bulk score all reels
        │       → All saved to Supabase
        │
        ├─ [Tab 3: 📈 Patterns]  ← Requires 5+ reels
        │       View personal benchmarks
        │       → Generate AI insights + roadmap
        │
        ├─ [Tab 4: 🎯 Pre-Score]
        │       Plan next reel
        │       → Pre-production score + AI tips
        │
        ├─ [Tab 5: 📝 Brief]
        │       Enter topic + goal
        │       → Personalised content brief from GPT
        │
        ├─ [Tab 6: 📧 Digest]
        │       Weekly performance snapshot
        │       → In-app preview + email delivery
        │
        ├─ [Tab 7: 🗓 Monthly]
        │       Select month
        │       → Growth Score card + MoM comparison
        │
        └─ [Tab 8: 🏆 Benchmark]
                Auto-detect tier + category
                → Industry comparison + opportunity cards
```

### Recommended Onboarding Path

1. **Sign up** — create account
2. **Import** (Tab 2) — upload Meta CSV to populate reel history quickly
3. **Analyse** (Tab 1) — deep-dive on one underperforming reel to understand the scoring logic
4. **Patterns** (Tab 3) — once 5+ reels exist, see personal trends
5. **Pre-Score** (Tab 4) — before filming the next reel
6. **Brief** (Tab 5) — generate a production brief for the planned topic
7. **Digest** (Tab 6) — set up weekly email snapshot
8. **Benchmark** (Tab 8) — understand where performance sits vs. industry

---

## 6. Diagnostic Scoring Engine

### Retention Ratio

```
retention_ratio = (watch_time_minutes × 60 / views) / reel_duration_seconds
```

Alternatively, if `avg_watch_seconds` is available directly from Meta export, that is used.

**Category benchmarks:**

| Category | Poor | Average | Good |
|---|---|---|---|
| Educational | < 30% | 30 – 50% | ≥ 50% |
| Inspirational | < 25% | 25 – 45% | ≥ 45% |
| Transactional | < 35% | 35 – 55% | ≥ 55% |
| Aesthetic | < 20% | 20 – 40% | ≥ 40% |
| Entertainment | < 25% | 25 – 50% | ≥ 50% |

### Engagement Rate

```
engagement_rate = (likes + comments + shares + saves) / views
```

**Follower tier benchmarks:**

| Tier | Poor | Average | Good |
|---|---|---|---|
| < 1K | < 3% | 3 – 6% | ≥ 6% |
| 1K – 5K | < 2% | 2 – 5% | ≥ 5% |
| 5K – 10K | < 1.5% | 1.5 – 4% | ≥ 4% |

### Hook Score

```
score = (count of HOOK_TRIGGERS in caption) × 2.5, capped at 10
penalty = −2 pts if opening line > 15 words
```

Hook triggers include: `you`, `why`, `how`, `secret`, `mistake`, `never`, `always`, `stop`, `truth`, `warning`, `finally`, `revealed`, `proven`, `what if`, `did you`, `most people`, `nobody talks`.

**Labels:** Weak (< 4), Moderate (4 – 6.9), Strong (≥ 7)

### Save Rate

```
save_rate = saves / views
```

**Labels:** Low (< 1%), Average (1 – 2%), Good (2 – 5%), Excellent (≥ 5%)

---

## 7. Design System

Implemented in `theme_engine.py`. All visual tokens are injected as CSS custom properties on `:root` via `inject_design_system()`.

### Colour Tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#050505` | Page background |
| `--card` | `#111111` | Card surfaces |
| `--card-deep` | `#0D0D0D` | Input backgrounds |
| `--border` | `rgba(255,255,255,0.08)` | Card/input borders |
| `--border-light` | `rgba(255,255,255,0.05)` | Subtle dividers |
| `--text-primary` | `#FFFFFF` | Body text |
| `--text-secondary` | `#888888` | Labels, captions |
| `--text-muted` | `rgba(255,255,255,0.28)` | De-emphasised text |
| `--good` | `#00E5A0` | Positive/success green |
| `--average` | `#FFB020` | Warning amber |
| `--poor` | `#FF3D71` | Negative pink-red |

### Instagram Gradient

```css
linear-gradient(90deg, #833AB4 0%, #E1306C 50%, #FCB045 100%)
```

Used on: logo wordmark, button fills, card accent bars, score rings, section label decorators.

### Typography

| Property | Value |
|---|---|
| Font family | Inter (300, 400, 500, 600, 700, 800, 900) |
| Header letter-spacing | -0.02em |
| Label letter-spacing | +0.12em (uppercase micro-labels) |
| Body size | 0.875rem (14px) |
| Micro-label size | 0.58 – 0.68rem |

### Logo (`get_logo_html`)

```
"Reel" — Inter weight 300
"IQ"   — Inter weight 800
Both rendered with background-clip: text and the Instagram gradient
```

### Component Library

**Rio Card (`rio_card(title, content, color_type)`)**

Unified content card used across all 8 phases. Three variants:

| Variant | Top Accent | Glow |
|---|---|---|
| `"default"` | Instagram gradient | None |
| `"success"` | Green (#00B37A → #00E5A0) | Subtle green box-shadow |
| `"alert"` | Orange (#CC8800 → #FCB045) | Subtle orange box-shadow |

**Buttons**

- Primary: Instagram gradient fill, 12px radius, 3rem height, 700 weight uppercase
- Ghost: Transparent + border, 8px radius, 2.2rem height — used for secondary actions (Regenerate, Refresh)
- Download: Transparent + subtle border (Streamlit `stDownloadButton` override)

**Score/Growth Ring**

SVG `<circle>` with `stroke-dashoffset` calculated from score percentage. Used in Pre-Score (Phase 4), Monthly Card (Phase 7), and Benchmark (Phase 8).

**Metric Grid**

2 × 2 or 1 × 4 grid of score cards. Each card: label (uppercase, muted), value (large, bold, colour-coded), tier tag chip.

**Section Labels**

Uppercase micro-labels with decorative right-side gradient line. Format: `01 — REEL METRICS`.

**Tabs**

8-tab navigation bar with `overflow-x: auto`, `flex-wrap: nowrap`, and hidden scrollbar — all 8 tabs accessible without wrapping.

---

## 8. Data Privacy & Security

### What Data Is Collected

| Data Type | Where Stored | Retention |
|---|---|---|
| Email address | Supabase Auth | Until account deleted |
| Hashed password | Supabase Auth (never plaintext) | Until account deleted |
| Reel metrics (views, likes, etc.) | Supabase Postgres | Until user deletes |
| AI-generated reports | Supabase Postgres | Until user deletes |
| Session tokens | Browser session state (memory only) | Until browser tab closed |

### What Data Is NOT Collected

- No names, phone numbers, or payment information
- No Instagram credentials (we never connect to the Instagram API)
- No device fingerprinting or analytics tracking
- CSV files are processed in-memory and never persisted to disk or the database; only the extracted numeric metrics are saved

### Authentication Security

- **Password storage:** Supabase Auth stores only bcrypt-hashed passwords. Plaintext passwords are never visible to application code.
- **Token handling:** Access tokens (short-lived) and refresh tokens (long-lived) are held only in `st.session_state`, which is server-side memory tied to a single browser session. Tokens are cleared immediately on logout.
- **Retry logic:** All Supabase API calls use a `_retry()` wrapper (3 attempts, 3-second delay) to handle cold starts on Supabase's free tier without exposing errors to the user.
- **Password reset:** Handled entirely by Supabase's built-in recovery flow — the app only triggers `auth.reset_password_for_email()` and never handles reset tokens directly.

### CSV Data Handling

1. The uploaded file is read into a Pandas DataFrame in memory.
2. Numeric fields are extracted and normalised; the original file object is discarded.
3. Only the processed metric values (integers and floats) are saved to Supabase — never the raw CSV file, column headers, or caption text beyond what the user explicitly inputs.
4. Rows with 0 views are silently skipped and never stored.

### OpenAI API Usage

- Metric data and caption text are sent to OpenAI's API only to generate reports, tips, briefs, and insights.
- No user email addresses, account identifiers, or Supabase IDs are included in any OpenAI prompt.
- All prompts are constructed with fixed system messages; user-supplied text is passed as the `user` role message only.
- OpenAI's standard data processing terms apply. No data is used to train models under the default API policy.

### Supabase Row-Level Security

- Each `reel_analyses` record is associated with a `user_id` column.
- Row-Level Security (RLS) policies on the Supabase table ensure users can only read and write their own rows; no cross-user data access is possible at the database level.

---

## 9. Session State Reference

All keys are initialised in `_defaults` at app startup:

| Key | Type | Purpose |
|---|---|---|
| `authenticated` | bool | Controls auth/app routing |
| `user_id` | str \| None | Supabase UUID |
| `user_email` | str \| None | Display + digest target |
| `access_token` | str \| None | Supabase API auth |
| `refresh_token` | str \| None | Token renewal |
| `save_status` | str \| None | Last reel save result |
| `save_error_msg` | str | Error detail if save failed |
| `patterns_data` | dict \| None | Computed pattern benchmarks |
| `patterns_insights` | str \| None | GPT-generated pattern narrative |
| `patterns_roadmap` | list \| None | Priority action items |
| `patterns_loaded` | bool | Fetch-once flag |
| `forgot_pw_mode` | bool | Password reset UI toggle |
| `forgot_pw_sent` | bool | Recovery email sent flag |
| `ps_result` | dict \| None | Pre-score calculation output |
| `ps_tips` | str \| None | GPT pre-production tips |
| `brief_result` | str \| None | Raw GPT brief response |
| `brief_topic` | str | User-entered topic (persisted across reruns) |
| `brief_goal` | str | Selected goal (persisted) |
| `digest_data` | dict \| None | Computed weekly digest |
| `digest_sent` | bool | Email delivery status |
| `digest_send_msg` | str | Delivery status message |
| `monthly_data` | dict \| None | Computed monthly card |
| `monthly_year` | int \| None | Selected year |
| `monthly_month` | int \| None | Selected month (1 – 12) |
| `benchmark_data` | dict \| None | Industry benchmark report |

---

## 10. Module Reference

| File | Exports | Description |
|---|---|---|
| `app.py` | — | Main application entry point; all 8 render functions; CSS injection; routing |
| `theme_engine.py` | `set_page_config`, `inject_design_system`, `get_logo_html`, `rio_card` | Complete design system — tokens, CSS, logo, card component |
| `diagnostic_engine.py` | `run_diagnostic` | Scores retention, engagement, hook, save rate against calibrated benchmarks |
| `ai_report.py` | `generate_ai_report`, `generate_pre_score_tips`, `generate_content_brief` | GPT-4o mini prompt construction and response parsing |
| `supabase_client.py` | `sign_up`, `sign_in`, `reset_password_email`, `save_reel_analysis`, `get_user_reels` | All Supabase auth and data operations |
| `patterns.py` | `compute_patterns`, `generate_ai_content`, `MIN_REELS` | Personal benchmark aggregation; AI insight generation |
| `pre_score_engine.py` | `run_pre_score` | Pre-production scoring across 4 components (0 – 100) |
| `email_digest.py` | `build_digest_data`, `build_digest_html`, `send_digest_email` | Weekly performance digest construction and email delivery |
| `monthly_card.py` | `compute_monthly_card` | Monthly Growth Score composite + month-over-month comparison |
| `competitor.py` | `compute_benchmark_report`, `INDUSTRY_BENCHMARKS` | 20-entry benchmark lookup (5 categories × 4 tiers); grading engine |

---

*Document generated from final application state. All 8 phases implemented and verified.*
