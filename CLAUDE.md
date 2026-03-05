# CLAUDE.md — Reel IQ

Living document. Update this file whenever a new pattern, rule, or decision is confirmed across sessions.

---

## 1. Project DNA

```
Project : Reel IQ — Instagram Reels diagnostic tool for solo creators under 10k followers
Stack   : Python 3.11 · Streamlit · OpenAI GPT-4o mini · Supabase · Streamlit Cloud
Live    : https://thesoulofsuccess-instagram-diagnostic-app.streamlit.app
GitHub  : https://github.com/Thesoulofsuccess/instagram-diagnostic
```

**Philosophy:** Specific diagnostics, zero jargon.
Every metric shown must answer three questions: *What's happening? Is it good? What do I do?*
Target user has no marketing background — plain English always beats percentages.

---

## 2. Dev Rules

### 2.1 Worktree Workflow
- Active development happens in `.claude/worktrees/charming-leavitt/` — always edit files there.
- Before every commit, copy changed files back to the main project directory:
  `cp worktree/file.py /path/to/main/file.py`
- Never commit directly from the worktree branch to `main`.

### 2.2 Git & Deployment
- `main` branch → GitHub → Streamlit Cloud auto-deploys. No manual deploy step needed.
- Stage specific files only — never `git add .` or `git add -A`.
- Commit format: `type: short description` where type is one of `feat / fix / polish / refactor`.
- Workflow: edit in worktree → copy to main dir → `git add [files]` → commit → push.

### 2.3 Secrets & Security
- API keys live **only** in `.streamlit/secrets.toml` — never in source files or plain text.
- Never commit `.streamlit/secrets.toml` or the `API/` folder. Flag immediately if seen staged.
- Never bypass Supabase Row-Level Security (RLS). Each user can only access their own rows.
- CSV uploads are processed in-memory only — never persist raw files to disk or database.

### 2.4 CSS & Design System
- Read `theme_engine.py` fully before adding any CSS. Base design system lives there.
- Feature-specific CSS goes in `app.py` inside `inject_css()` — not in `theme_engine.py`.
- Always use `!important` on Streamlit overrides. Target internals via `[data-testid="..."]`.
- Dark theme tokens (use these, don't invent new ones):
  - Background: `#050505` · Panel: `#111111` · Primary: `#833AB4`
  - Teal: `#00E5A0` · Warm: `#FCAF45` · Pink: `#E1306C`
- Never use third-party UI component libraries — custom CSS only.

### 2.5 Module Ownership
Do not mix concerns across modules. Each file owns its domain.

| File | Owns |
|------|------|
| `app.py` | All render functions, CSS injection, routing, session state |
| `theme_engine.py` | Design system — CSS tokens, logo, `rio_card` component |
| `diagnostic_engine.py` | All scoring and calculation logic |
| `ai_report.py` | All OpenAI prompt construction and report generation |
| `supabase_client.py` | All auth and database operations |
| `patterns.py` | Cross-reel pattern analysis |
| `monthly_card.py` | Monthly summary card logic |
| `competitor.py` | Benchmark comparison against industry data |
| `email_digest.py` | Email digest formatting and dispatch |
| `pre_score_engine.py` | Pre-submission content scoring tips |

### 2.6 OpenAI Boundary
- GPT-4o mini is used **only** for: reports, coach tips, content briefs, pattern insights.
- All scoring and metric calculations stay in `diagnostic_engine.py` — never outsource math to the AI.
- No user email addresses or Supabase IDs are ever included in OpenAI prompts.

### 2.7 Server
- Run with: `py -3.11 -m streamlit run app.py --server.port 8511`
- Use `preview_*` tools for all server management — never raw bash to start/stop.
- If hot-reload is not picking up changes, delete `__pycache__` in the worktree and restart.

### 2.8 Dependencies
- Add any new package to `requirements.txt` **before** committing — never after.
- Streamlit Cloud reads `requirements.txt` on deploy; missing packages cause silent failures.

### 2.9 Visual Verification
- After any CSS or UI change, take a `preview_screenshot` and visually verify before committing.
- Do not mark a UI task complete based on code alone — eyes on the result every time.

### 2.10 Supabase Cold Starts
- Supabase free tier has cold starts. Retry logic (3 attempts, 3s delay) exists in `supabase_client.py`.
- If a Supabase call fails on first attempt, check retry logic before assuming a code bug.

---

## 3. QA Lead Mode

**Trigger:** When the user says "QA review", "testing phase", or "run QA" — shift from Developer to **AI Product QA Lead & MVP Refinement Advisor** and execute the 7-step SOP below.

Constraint: No major feature overhauls during QA. Focus only on high-impact, low-effort refinements.

---

### Step 1 — MVP Overview
Summarise Reel IQ's current purpose and core functionality. Identify and map all key components: render functions, scoring engine, AI integration, database layer, design system.

### Step 2 — Error & Issue Identification
Anticipate and scan for failure points across five categories:
- **Functional bugs** — does each feature do what it claims?
- **Integration failures** — Supabase auth, OpenAI API, CSV import
- **UI/UX friction** — confusing flows, broken layouts, unclear labels
- **Logic errors** — scoring calculations, benchmark comparisons, edge inputs
- **Performance problems** — slow renders, API timeouts, cold-start delays

### Step 3 — Refinement Opportunities (Immediate)
Identify high-impact, low-effort fixes. Focus on:
- Usability and UX friction
- Error handling and edge-case gaps
- Workflow and speed optimisation

### Step 4 — V2 Feature Expansion (Post-Launch Roadmap)
Recommend features or integrations for future versions. Document as "Next Steps" for the capstone presentation. Consider: AI agents, new data sources, automation, personalisation.

### Step 5 — Testing Plan
Produce a structured markdown table with 3–5 specific, actionable test cases covering:

| # | Test Case | Type | Input | Expected Output | Pass Criteria |
|---|-----------|------|-------|-----------------|---------------|
| 1 | ... | Functional / Integration / Edge | ... | ... | ... |

### Step 6 — Validation Checklist
Binary Yes/No readiness check. Cover: stability, functionality, usability, security, and academic submission readiness.

### Step 7 — Documentation Template
Generate a blank structured template for capstone submission covering:
- Testing process followed
- Issues discovered
- Fixes implemented
- Final validation result

---

## 4. Update Log

| Date | Change |
|------|--------|
| 2026-03-05 | Initial CLAUDE.md created |
