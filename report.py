"""
Reddit Stock Radar — Daily Report Generator
Runs via GitHub Actions each weekday morning.
Produces three sections:
  1. Reddit trending picks
  2. Executive branch / White House policy-aligned trades (OGE filings)
  3. Congressional STOCK Act filings (new disclosures only)
Saves an HTML dashboard to reports/latest.html and an archive copy.
"""

import anthropic
import json
import re
import os
import datetime

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")

TODAY      = datetime.date.today().strftime("%A, %B %d, %Y")
TODAY_SLUG = datetime.date.today().strftime("%Y-%m-%d")
OUTPUT_DIR = "reports"
OUTPUT_LATEST  = os.path.join(OUTPUT_DIR, "latest.html")
OUTPUT_ARCHIVE = os.path.join(OUTPUT_DIR, f"{TODAY_SLUG}.html")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Prompts ───────────────────────────────────────────────────────────────────

REDDIT_PROMPT = f"""You are a financial analyst. Search the web for the most actively discussed stock picks on Reddit today ({TODAY}) across r/wallstreetbets, r/smallstreetbets, r/stocks, r/investing, r/pennystocks, and r/options.

Find:
1. Trending tickers being discussed today
2. Stocks with the most mentions this week
3. Any notable options plays, momentum trades, or catalysts being debated

Return ONLY a valid JSON object, no markdown, no preamble:
{{
  "date": "{TODAY}",
  "headline": "One analytical sentence summarizing today's Reddit market sentiment",
  "market_mood": "bullish" | "bearish" | "neutral" | "mixed",
  "stocks": [
    {{
      "ticker": "AAPL",
      "company": "Apple Inc.",
      "sentiment": "bullish" | "bearish" | "neutral",
      "sources": ["wallstreetbets", "stocks"],
      "mentions": 342,
      "summary": "Factual 1-2 sentence summary of the thesis being discussed.",
      "bull_case": "The specific bullish argument with supporting data points.",
      "bear_case": "The specific bearish argument with supporting data points.",
      "catalysts": "Concrete upcoming catalysts: earnings date, product launches, macro events.",
      "price_target": "Analyst consensus or community price target with timeframe, e.g. $210 by Q3 2026",
      "risk_level": "LOW" | "MED" | "HIGH" | "YOLO"
    }}
  ]
}}

Include 6-9 stocks. Be specific and factual."""

POLICY_PROMPT = f"""You are a financial analyst tracking government financial disclosures. Today is {TODAY}.

Search the web for:
1. The most recent OGE Form 278-T filings from President Trump and executive branch officials
2. Any new or notable trades disclosed in the past 7 days by White House staff or cabinet members
3. Cross-reference those holdings against active administration policies (tariffs, deregulation, export waivers, federal contracts, legislation) that directly benefit those positions
4. Specific analyst price targets for each identified stock

For each high-conviction policy-aligned position, provide a strictly analytical assessment. Do not editorialize. Simply document the disclosed holding, the policy overlap, and the investment case.

Return ONLY valid JSON, no markdown, no preamble:
{{
  "last_filing_date": "Date of most recent OGE filing referenced",
  "summary": "One sentence factual summary of the executive branch disclosure landscape",
  "picks": [
    {{
      "ticker": "NVDA",
      "company": "Nvidia Corporation",
      "disclosed_by": ["Donald Trump", "Cabinet member name"],
      "filing_date": "2026-05-14",
      "trade_type": "BUY" | "SELL" | "HOLD",
      "policy_link": "Specific policy action that creates a direct financial benefit, with date",
      "investment_thesis": "Analytical case for why this holding has continued upside, with specific data.",
      "price_target": "Analyst consensus target and timeframe",
      "conviction": "HIGH" | "MEDIUM" | "LOW",
      "risk": "Specific downside risk to this thesis"
    }}
  ]
}}

Include 5-10 picks. Cite specific filing dates, policy names, and price targets where available."""

CONGRESS_PROMPT = f"""You are a financial analyst tracking congressional stock disclosures. Today is {TODAY}.

Search the web for:
1. The most recent STOCK Act periodic transaction reports filed by U.S. senators and representatives in the past 14 days
2. Any notable trades by members of committees with direct oversight of relevant industries (Armed Services, Finance, Banking, Intelligence, Commerce, Energy)
3. Cross-reference those trades against legislation, hearings, or policy activity in their committees
4. Analyst price targets for each identified stock

Focus on NEW disclosures — trades filed or reported in the last 14 days. Flag the committee relevance and any timing coincidences with legislation or hearings.

Return ONLY valid JSON, no markdown, no preamble:
{{
  "period_covered": "Date range of filings reviewed",
  "total_new_filings": 12,
  "summary": "One factual sentence about the most notable pattern in recent congressional trading",
  "trades": [
    {{
      "ticker": "LMT",
      "company": "Lockheed Martin",
      "disclosed_by": "Sen. Jane Smith (R-TX)",
      "committee": "Senate Armed Services Committee",
      "filing_date": "2026-05-20",
      "trade_date": "2026-05-15",
      "trade_type": "BUY" | "SELL",
      "amount_range": "$15,001 - $50,000",
      "committee_relevance": "Specific bill, hearing, or vote in their committee that overlaps with this trade",
      "investment_thesis": "Analytical case for this stock given the disclosed interest and policy context",
      "price_target": "Analyst consensus target and timeframe",
      "conviction": "HIGH" | "MEDIUM" | "LOW",
      "risk": "Key downside risk"
    }}
  ]
}}

Include all material new filings up to 10. Be specific about names, dates, and committee roles."""

# ── API calls ─────────────────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=API_KEY)

def call_claude(prompt, label):
    print(f"[{TODAY_SLUG}] Fetching: {label}...")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in resp.content if hasattr(b, "text"))
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError(f"No JSON in {label} response:\n{raw[:500]}")
    return json.loads(m.group())

reddit_data  = call_claude(REDDIT_PROMPT,  "Reddit picks")
policy_data  = call_claude(POLICY_PROMPT,  "Executive branch filings")
congress_data = call_claude(CONGRESS_PROMPT, "Congressional STOCK Act filings")

print(f"[{TODAY_SLUG}] All sections fetched. Building dashboard...")

# ── Helpers ───────────────────────────────────────────────────────────────────

MOOD_COLOR = {"bullish":"#00ff9f","bearish":"#ff4d6d","neutral":"#f0c040","mixed":"#7eb8ff"}
MOOD_ICON  = {"bullish":"▲","bearish":"▼","neutral":"◆","mixed":"⇄"}
SENT_COLOR = {"bullish":"#00ff9f","bearish":"#ff4d6d","neutral":"#f0c040"}
RISK_COLOR = {"LOW":"#00ff9f","MED":"#f0c040","HIGH":"#ff8c42","YOLO":"#ff4d6d"}
CONV_COLOR = {"HIGH":"#00ff9f","MEDIUM":"#f0c040","LOW":"#aaa"}
TRADE_COLOR = {"BUY":"#00ff9f","SELL":"#ff4d6d","HOLD":"#f0c040"}

def badge(text, color="#888", bg="rgba(255,255,255,0.06)"):
    return (f'<span style="font-size:10px;font-weight:600;padding:2px 9px;border-radius:20px;'
            f'border:1px solid {color}40;color:{color};background:{bg};display:inline-block;'
            f'margin:2px 3px 2px 0;">{text}</span>')

def risk_badge(risk):
    rc = RISK_COLOR.get(risk, "#888")
    return f'<span style="font-size:10px;font-weight:700;padding:3px 9px;border-radius:3px;background:{rc};color:#000;">{risk}</span>'

def conviction_badge(c):
    cc = CONV_COLOR.get(c, "#888")
    return badge(f"● {c} CONVICTION", cc)

def trade_type_badge(t):
    tc = TRADE_COLOR.get(t, "#888")
    return f'<span style="font-size:11px;font-weight:700;padding:3px 10px;border-radius:3px;background:{tc}22;border:1px solid {tc}55;color:{tc};">{t}</span>'

def source_badges(sources):
    return "".join(badge(f"r/{s}", "#666") for s in (sources or []))

def expandable_card(card_id, border_color, header_html, body_html):
    return f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
         border-left:3px solid {border_color};border-radius:6px;margin-bottom:10px;overflow:hidden;">
      <div onclick="toggle('{card_id}')"
           style="padding:16px 20px;cursor:pointer;"
           onmouseover="this.style.background='rgba(255,255,255,0.04)'"
           onmouseout="this.style.background='transparent'">
        {header_html}
        <span id="{card_id}_arr" style="float:right;color:#555;font-size:16px;margin-top:-20px;">+</span>
      </div>
      <div id="{card_id}" style="display:none;padding:0 20px 18px;border-top:1px solid rgba(255,255,255,0.07);">
        <div style="padding-top:14px;display:grid;gap:12px;">
          {body_html}
        </div>
      </div>
    </div>"""

def detail_row(label, color, content):
    return f"""<div>
      <div style="font-size:10px;font-weight:700;letter-spacing:.09em;color:{color};margin-bottom:3px;">{label}</div>
      <p style="color:#bbb;font-size:13px;line-height:1.6;margin:0;">{content}</p>
    </div>"""

# ── Section 1: Reddit cards ───────────────────────────────────────────────────

def reddit_card(s, idx):
    sc  = SENT_COLOR.get(s.get("sentiment","neutral"), "#f0c040")
    si  = MOOD_ICON.get(s.get("sentiment","neutral"), "◆")
    cid = f"r_{idx}"
    header = f"""
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="font-family:monospace;font-size:18px;font-weight:700;color:#fff;">${s.get('ticker','?')}</span>
          <span style="color:#888;font-size:13px;margin-left:10px;">{s.get('company','')}</span>
          {'<span style="color:#aaa;font-size:11px;margin-left:8px;">🔥 '+str(s.get('mentions',''))+ ' mentions</span>' if s.get('mentions') else ''}
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          {risk_badge(s.get('risk_level','MED'))}
          <span style="color:{sc};font-size:11px;font-weight:700;text-transform:uppercase;">{si} {s.get('sentiment','')}</span>
        </div>
      </div>
      <div style="margin-top:6px;">{source_badges(s.get('sources',[]))}</div>
      <p style="margin:8px 0 0;color:#bbb;font-size:13.5px;line-height:1.6;">{s.get('summary','')}</p>"""
    body = (
        detail_row("▲ BULL CASE", "#00ff9f", s.get('bull_case','—')) +
        detail_row("▼ BEAR CASE", "#ff4d6d", s.get('bear_case','—')) +
        detail_row("◆ CATALYSTS", "#f0c040", s.get('catalysts','—')) +
        detail_row("⊕ PRICE TARGET", "#7eb8ff", s.get('price_target','Not specified'))
    )
    return expandable_card(cid, sc, header, body)

# ── Section 2: Policy / executive cards ──────────────────────────────────────

def policy_card(p, idx):
    conv  = p.get("conviction","MEDIUM")
    cc    = CONV_COLOR.get(conv, "#aaa")
    ttype = p.get("trade_type","BUY")
    tc    = TRADE_COLOR.get(ttype, "#888")
    cid   = f"p_{idx}"
    disclosers = ", ".join(p.get("disclosed_by") or [])
    header = f"""
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="font-family:monospace;font-size:18px;font-weight:700;color:#fff;">${p.get('ticker','?')}</span>
          <span style="color:#888;font-size:13px;margin-left:10px;">{p.get('company','')}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          {trade_type_badge(ttype)}
          {conviction_badge(conv)}
        </div>
      </div>
      <div style="margin-top:6px;">
        {badge('Disclosed by: '+disclosers, '#aaa')}
        {badge('Filed: '+p.get('filing_date','?'), '#666')}
      </div>
      <p style="margin:8px 0 0;color:#bbb;font-size:13.5px;line-height:1.6;">{p.get('investment_thesis','')[:180]}{'...' if len(p.get('investment_thesis',''))>180 else ''}</p>"""
    body = (
        detail_row("⚖ POLICY OVERLAP", "#bf5af2", p.get('policy_link','—')) +
        detail_row("📈 INVESTMENT THESIS", "#7eb8ff", p.get('investment_thesis','—')) +
        detail_row("⊕ ANALYST TARGET", "#00ff9f", p.get('price_target','Not specified')) +
        detail_row("⚠ DOWNSIDE RISK", "#ff8c42", p.get('risk','—'))
    )
    return expandable_card(cid, cc, header, body)

# ── Section 3: Congressional STOCK Act cards ──────────────────────────────────

def congress_card(t, idx):
    ttype = t.get("trade_type","BUY")
    tc    = TRADE_COLOR.get(ttype, "#888")
    conv  = t.get("conviction","MEDIUM")
    cc    = CONV_COLOR.get(conv,"#aaa")
    cid   = f"c_{idx}"
    header = f"""
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="font-family:monospace;font-size:18px;font-weight:700;color:#fff;">${t.get('ticker','?')}</span>
          <span style="color:#888;font-size:13px;margin-left:10px;">{t.get('company','')}</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          {trade_type_badge(ttype)}
          {conviction_badge(conv)}
        </div>
      </div>
      <div style="margin-top:6px;">
        {badge(t.get('disclosed_by','?'), '#aaa')}
        {badge(t.get('committee','?'), '#7eb8ff')}
        {badge('Filed '+t.get('filing_date','?'), '#666')}
        {badge('Trade date '+t.get('trade_date','?'), '#666')}
        {badge(t.get('amount_range','?'), '#888')}
      </div>
      <p style="margin:8px 0 0;color:#bbb;font-size:13.5px;line-height:1.6;">{t.get('investment_thesis','')[:180]}{'...' if len(t.get('investment_thesis',''))>180 else ''}</p>"""
    body = (
        detail_row("🏛 COMMITTEE RELEVANCE", "#bf5af2", t.get('committee_relevance','—')) +
        detail_row("📈 INVESTMENT THESIS", "#7eb8ff", t.get('investment_thesis','—')) +
        detail_row("⊕ ANALYST TARGET", "#00ff9f", t.get('price_target','Not specified')) +
        detail_row("⚠ DOWNSIDE RISK", "#ff8c42", t.get('risk','—'))
    )
    return expandable_card(cid, tc, header, body)

# ── Build HTML ────────────────────────────────────────────────────────────────

reddit_stocks = reddit_data.get("stocks", [])
policy_picks  = policy_data.get("picks", [])
congress_trades = congress_data.get("trades", [])

mood    = reddit_data.get("market_mood","neutral")
mc      = MOOD_COLOR.get(mood,"#888")
mi      = MOOD_ICON.get(mood,"◆")
bull_n  = sum(1 for s in reddit_stocks if s.get("sentiment")=="bullish")
bear_n  = sum(1 for s in reddit_stocks if s.get("sentiment")=="bearish")

reddit_cards_html  = "".join(reddit_card(s, i)  for i, s in enumerate(reddit_stocks))
policy_cards_html  = "".join(policy_card(p, i)  for i, p in enumerate(policy_picks))
congress_cards_html = "".join(congress_card(t, i) for i, t in enumerate(congress_trades))

archive_files = sorted(
    [f for f in os.listdir(OUTPUT_DIR) if re.match(r"\d{4}-\d{2}-\d{2}\.html", f)],
    reverse=True
)[:7]
archive_links = "".join(
    f'<a href="{f}" style="color:#555;font-size:12px;font-family:monospace;text-decoration:none;'
    f'padding:4px 10px;border:1px solid rgba(255,255,255,0.07);border-radius:4px;">'
    f'{f.replace(".html","")}</a>' for f in archive_files
)

def section_header(icon, title, subtitle, border_color):
    return f"""
    <div style="display:flex;align-items:center;gap:14px;margin:32px 0 14px;padding-bottom:10px;
         border-bottom:1px solid rgba(255,255,255,0.07);">
      <span style="font-size:20px;">{icon}</span>
      <div>
        <div style="font-family:monospace;font-size:13px;font-weight:700;color:{border_color};
             letter-spacing:.06em;">{title}</div>
        <div style="font-size:11px;color:#555;margin-top:1px;">{subtitle}</div>
      </div>
    </div>"""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reddit Radar — {TODAY}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background:#0a0b0e; color:#fff; font-family:'DM Sans',sans-serif; min-height:100vh; padding:0 0 60px; }}
  .wrap {{ max-width:880px; margin:0 auto; padding:24px 18px; }}
  .header {{ display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;
             border-bottom:1px solid rgba(255,255,255,0.07);padding-bottom:18px;margin-bottom:20px; }}
  .mood-banner {{ background:linear-gradient(135deg,{mc}18 0%,transparent 60%);
                  border:1px solid {mc}30;border-radius:8px;padding:16px 20px;margin-bottom:20px; }}
  .stats {{ display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:28px; }}
  .stat {{ background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:5px;padding:10px 14px; }}
  .disclaimer {{ margin-top:24px;padding:12px 16px;background:rgba(255,255,255,0.03);
                 border:1px solid rgba(255,255,255,0.08);border-radius:5px;
                 font-size:11px;color:#555;line-height:1.7; }}
  .archive {{ display:flex;flex-wrap:wrap;gap:8px;margin-top:10px; }}
  @media(max-width:500px) {{ .stats {{ grid-template-columns:1fr 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div>
      <div style="font-family:monospace;font-size:11px;color:#00ff9f;letter-spacing:.15em;font-weight:700;">📡 REDDIT RADAR</div>
      <div style="font-family:monospace;font-size:clamp(17px,4vw,23px);font-weight:700;letter-spacing:-.02em;margin-top:4px;">Daily Stock Intelligence</div>
      <div style="font-size:12px;color:#555;margin-top:2px;">{reddit_data.get('date', TODAY)}</div>
    </div>
    <div style="font-family:monospace;font-size:12px;font-weight:700;color:{mc};text-transform:uppercase;
         letter-spacing:.12em;padding:8px 16px;border:1px solid {mc}40;border-radius:4px;background:{mc}10;">
      {mi} {mood.upper()}
    </div>
  </div>

  <div class="mood-banner">
    <div style="font-size:11px;color:#555;letter-spacing:.1em;font-family:monospace;margin-bottom:4px;">TODAY'S MARKET SENTIMENT</div>
    <div style="font-size:15px;color:#ddd;font-weight:500;line-height:1.5;">{reddit_data.get('headline','')}</div>
  </div>

  <div class="stats">
    <div class="stat"><div style="font-size:10px;color:#555;letter-spacing:.1em;">REDDIT PICKS</div><div style="font-size:22px;font-weight:700;">{len(reddit_stocks)}</div></div>
    <div class="stat"><div style="font-size:10px;color:#555;letter-spacing:.1em;">BULLISH</div><div style="font-size:22px;font-weight:700;color:#00ff9f;">{bull_n}</div></div>
    <div class="stat"><div style="font-size:10px;color:#555;letter-spacing:.1em;">BEARISH</div><div style="font-size:22px;font-weight:700;color:#ff4d6d;">{bear_n}</div></div>
  </div>

  {section_header("💬", "REDDIT TRENDING PICKS", "Most discussed stocks across r/wallstreetbets, r/smallstreetbets, r/stocks, r/investing & more · Tap to expand", "#00ff9f")}
  {reddit_cards_html}

  {section_header("🏛", "EXECUTIVE BRANCH POLICY TRADES", f"OGE Form 278-T disclosures · Most recent filing: {policy_data.get('last_filing_date','—')} · {policy_data.get('summary','')}", "#bf5af2")}
  <div style="font-size:11px;color:#555;margin-bottom:12px;">
    Cross-referencing publicly disclosed executive holdings against concurrent policy actions that directly affect those positions.
    Sources: U.S. Office of Government Ethics (OGE). All data from public filings.
  </div>
  {policy_cards_html if policy_cards_html else '<div style="color:#555;font-size:13px;padding:16px 0;">No new executive branch filings in the last 7 days.</div>'}

  {section_header("📋", "CONGRESSIONAL STOCK ACT FILINGS — NEW THIS WEEK", f"Periodic transaction reports filed in the last 14 days · {congress_data.get('total_new_filings',0)} new filings · {congress_data.get('summary','')}", "#7eb8ff")}
  <div style="font-size:11px;color:#555;margin-bottom:12px;">
    Period covered: {congress_data.get('period_covered','—')} ·
    Focus on members of Armed Services, Finance, Banking, Intelligence, Commerce & Energy committees.
    Sources: U.S. House and Senate STOCK Act disclosures.
  </div>
  {congress_cards_html if congress_cards_html else '<div style="color:#555;font-size:13px;padding:16px 0;">No new congressional filings detected in the last 14 days.</div>'}

  <div class="disclaimer">
    <b style="color:#888;">Disclaimer:</b> This report is for informational purposes only and does not constitute financial advice.
    Government disclosure data is sourced from public OGE and STOCK Act filings. Analyst price targets are sourced from public research.
    Past performance of policy-correlated trades does not guarantee future results.
    The legal status of the trading patterns documented here is a matter of ongoing public and legal debate.
  </div>

  {'<div style="margin-top:24px;"><div style="font-family:monospace;font-size:11px;color:#444;letter-spacing:.12em;margin-bottom:8px;">PAST REPORTS</div><div class="archive">'+archive_links+'</div></div>' if archive_links else ''}

</div>
<script>
function toggle(id) {{
  var el  = document.getElementById(id);
  var arr = document.getElementById(id+'_arr');
  var open = el.style.display !== 'none';
  el.style.display = open ? 'none' : 'block';
  arr.textContent  = open ? '+'    : '−';
}}
</script>
</body>
</html>"""

# ── Write output ──────────────────────────────────────────────────────────────

for path in [OUTPUT_LATEST, OUTPUT_ARCHIVE]:
    with open(path, "w", encoding="utf-8") as f:
        f.write(HTML)

print(f"[{TODAY_SLUG}] ✅ {OUTPUT_LATEST}")
print(f"[{TODAY_SLUG}] ✅ {OUTPUT_ARCHIVE}")
print(f"[{TODAY_SLUG}] Reddit: {len(reddit_stocks)} stocks | Executive: {len(policy_picks)} picks | Congress: {len(congress_trades)} trades")
