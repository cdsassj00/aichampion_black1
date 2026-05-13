#!/usr/bin/env python3
"""manifest.json + reports/*.html → dist/ 책자 생성.

- chapters/ : 원본 HTML을 그대로 복사 (iframe으로 로드)
- index.html : 발간사 표지 + 기수별 사이드바 목차 + 메인 iframe 뷰어
"""
from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
MANIFEST = ROOT / "data" / "manifest.json"
FOREWORD_MD = ROOT / "data" / "foreword.md"
REPORTS = ROOT / "reports"
# Output to /docs at repo root so GitHub Pages "Deploy from a branch" can serve it directly.
DIST = REPO_ROOT / "docs"
CHAPTERS = DIST / "chapters"


def sort_key(e: dict) -> tuple:
    return (int(e.get("cohort", "1")), e["org"], e["name"])


def safe_slug(s: str) -> str:
    return re.sub(r"[^\w가-힣\-]+", "_", s).strip("_")


def md_to_html(md: str) -> str:
    """발간사 전용 초미니 마크다운: # / ## 헤딩, **bold**, 빈 줄로 분리된 단락."""
    blocks = re.split(r"\n\s*\n", md.strip())
    out = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith("# "):
            out.append(f"<h1>{_inline(b[2:].strip())}</h1>")
        elif b.startswith("## "):
            out.append(f"<h2>{_inline(b[3:].strip())}</h2>")
        elif b.startswith("— ") or b.startswith("- "):
            out.append(f"<p class='sig'>{_inline(b)}</p>")
        else:
            out.append(f"<p>{_inline(b)}</p>")
    return "\n".join(out)


def _inline(s: str) -> str:
    s = escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def main() -> int:
    entries = json.loads(MANIFEST.read_text())
    ok = [e for e in entries if e.get("status") == "ok"]
    missing = [e for e in entries if e.get("status") != "ok"]
    ok.sort(key=sort_key)

    if DIST.exists():
        shutil.rmtree(DIST)
    CHAPTERS.mkdir(parents=True)

    chapters: list[dict] = []
    cohort_counts: dict[str, int] = {}
    for e in ok:
        c = str(e.get("cohort", "1"))
        cohort_counts[c] = cohort_counts.get(c, 0) + 1

    cohort_seen: dict[str, int] = {}
    for e in ok:
        cohort = str(e.get("cohort", "1"))
        cohort_seen[cohort] = cohort_seen.get(cohort, 0) + 1
        n_in_cohort = cohort_seen[cohort]
        slug = (
            f"c{cohort}_{n_in_cohort:02d}_{safe_slug(e['org'])}_{safe_slug(e['name'])}.html"
        )
        src = ROOT / e["local"]
        dst = CHAPTERS / slug
        shutil.copy2(src, dst)
        chapters.append({
            "cohort": cohort,
            "n": n_in_cohort,
            "global_n": len(chapters) + 1,
            "slug": slug,
            "name": e["name"],
            "org": e["org"],
            "repo": e.get("repo", ""),
        })

    # Group chapters by cohort for TOC
    cohorts: dict[str, list[dict]] = {}
    for c in chapters:
        cohorts.setdefault(c["cohort"], []).append(c)

    toc_html_parts = []
    for cohort in sorted(cohorts.keys(), key=int):
        items = cohorts[cohort]
        toc_html_parts.append(
            f'<li class="toc-section"><span class="section-label">{cohort}기 · {len(items)}편</span></li>'
        )
        for c in items:
            toc_html_parts.append(
                f'<li><a href="#" data-cohort="{c["cohort"]}" data-n="{c["n"]}">'
                f'<span class="num">{c["n"]:02d}</span>'
                f'<span class="meta"><span class="org">{escape(c["org"])}</span>'
                f'<span class="name">{escape(c["name"])}</span></span></a></li>'
            )
    toc_items = "\n".join(toc_html_parts)

    foreword_html = md_to_html(FOREWORD_MD.read_text())

    pending = (
        ('<div class="pending-block">'
         '<h3>합류 예정</h3>'
         '<ul>'
         + "".join(
            f"<li>{escape(m['org'])} / <strong>{escape(m['name'])}</strong> 리더 — 자료 합류 예정</li>"
            for m in missing
        )
         + '</ul>'
         '<p class="pending-note">2기 리더들의 보고서도 곧 이 책에 함께 엮입니다.</p>'
         '</div>')
        if missing
        else ""
    )

    cover_html = (
        '<div class="cover">'
        '<div class="kicker">AI 전문인재 과정 · 1일차 보고서 모음</div>'
        f'{foreword_html}'
        f'{pending}'
        '<p class="hint">← 왼쪽 목차에서 챕터를 선택하면 해당 리더의 보고서가 열립니다.</p>'
        '</div>'
    )

    index_html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>대한민국 AI 거점 리더 · SLM 모델 조사 보고서 모음집</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css" rel="stylesheet">
<style>
  :root {{
    --bg:#0b1220; --panel:#0f172a; --panel-2:#1e293b;
    --ink:#e2e8f0; --ink-mute:#94a3b8; --accent:#60a5fa; --accent-soft:#1e3a8a;
    --border:#1e293b;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    font-family: 'Pretendard Variable','Pretendard','Inter','Noto Sans KR',sans-serif;
    background: var(--bg); color: var(--ink);
    display: grid; grid-template-columns: 300px 1fr; height: 100vh;
    transition: grid-template-columns 0.2s ease;
  }}
  body.collapsed {{ grid-template-columns: 0 1fr; }}
  body.collapsed aside {{ opacity: 0; pointer-events: none; }}
  aside {{
    background: var(--panel); border-right: 1px solid var(--border);
    overflow-y: auto; display: flex; flex-direction: column;
  }}
  .brand {{
    padding: 20px 20px 14px; border-bottom: 1px solid var(--border);
    position: sticky; top: 0; background: var(--panel); z-index: 1;
  }}
  .brand .k {{ font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-mute); }}
  .brand .t {{ font-weight: 800; font-size: 17px; margin-top: 6px; line-height: 1.35; }}
  .brand .home {{
    display: inline-block; margin-top: 10px; font-size: 12px; color: var(--accent);
    text-decoration: none; cursor: pointer;
  }}
  .brand .home:hover {{ text-decoration: underline; }}
  ol.toc {{ list-style: none; padding: 8px 0 24px; margin: 0; }}
  ol.toc li.toc-section {{
    padding: 14px 16px 6px; font-size: 10px; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--ink-mute); font-weight: 700;
    border-top: 1px solid var(--border); margin-top: 6px;
  }}
  ol.toc li.toc-section:first-child {{ border-top: 0; margin-top: 0; }}
  ol.toc li a {{
    display: flex; align-items: center; gap: 10px;
    padding: 10px 16px; text-decoration: none; color: var(--ink);
    border-left: 3px solid transparent;
  }}
  ol.toc li a:hover {{ background: var(--panel-2); }}
  ol.toc li a.active {{ background: var(--accent-soft); border-left-color: var(--accent); }}
  ol.toc .num {{
    font-variant-numeric: tabular-nums; font-size: 11px;
    color: var(--ink-mute); width: 24px; flex: none;
  }}
  ol.toc .meta {{ display: flex; flex-direction: column; gap: 1px; min-width: 0; }}
  ol.toc .org {{ font-size: 11px; color: var(--ink-mute); }}
  ol.toc .name {{ font-size: 14px; font-weight: 600; }}

  main {{ position: relative; background: #f1f5f9; }}
  iframe {{ width: 100%; height: 100%; border: 0; background: white; }}

  .cover {{
    height: 100%; overflow-y: auto; padding: 72px 64px 96px;
    color: #0f172a; background: linear-gradient(180deg,#f8fafc, #e2e8f0);
    max-width: 880px; margin: 0 auto;
  }}
  .cover .kicker {{
    font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase;
    color: #475569; font-weight: 700;
  }}
  .cover h1 {{
    font-size: 40px; margin: 14px 0 28px; line-height: 1.2;
    letter-spacing: -0.02em; color: #0f172a;
  }}
  .cover h2 {{ font-size: 22px; margin: 36px 0 12px; color: #1e3a8a; letter-spacing: -0.01em; }}
  .cover p {{ font-size: 16px; line-height: 1.85; color: #1f2937; margin: 0 0 18px; }}
  .cover p strong {{ color: #0f172a; background: linear-gradient(transparent 62%, #dbeafe 62%); padding: 0 2px; }}
  .cover p.sig {{ margin-top: 36px; font-style: normal; font-weight: 600; color: #334155; text-align: right; }}
  .cover .hint {{
    margin-top: 56px; padding: 14px 18px; background: #fff;
    border-left: 3px solid #2563eb; border-radius: 4px;
    font-size: 14px; color: #1e3a8a; line-height: 1.6;
  }}
  .cover .pending-block {{
    margin-top: 40px; padding: 20px 22px; background: #fff7ed;
    border: 1px solid #fed7aa; border-radius: 8px;
  }}
  .cover .pending-block h3 {{
    font-size: 13px; letter-spacing: 0.12em; text-transform: uppercase;
    color: #9a3412; margin: 0 0 10px;
  }}
  .cover .pending-block ul {{ margin: 0; padding-left: 20px; font-size: 14px; color: #7c2d12; line-height: 1.7; }}
  .cover .pending-note {{ margin-top: 10px; font-size: 13px; color: #9a3412; }}

  .topbar {{
    position: absolute; top: 0; left: 0; right: 0; height: 48px;
    display: none; align-items: center; justify-content: space-between;
    padding: 0 14px; background: rgba(255,255,255,0.97); backdrop-filter: blur(8px);
    border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #334155; z-index: 5;
  }}
  .topbar.show {{ display: flex; }}
  .topbar .left {{ display: flex; align-items: center; gap: 10px; min-width: 0; }}
  .topbar .title {{ font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .topbar .nav {{ display: flex; align-items: center; gap: 6px; flex: none; }}
  .topbar .nav button, .topbar .nav .btn {{
    background: white; border: 1px solid #cbd5e1; padding: 5px 10px; border-radius: 5px;
    cursor: pointer; font-size: 12px; text-decoration: none; color: #334155;
    display: inline-flex; align-items: center; gap: 4px;
  }}
  .topbar .nav button:hover, .topbar .nav .btn:hover {{ background: #f1f5f9; }}
  .topbar .nav button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .topbar .nav .primary {{ background: #2563eb; border-color: #2563eb; color: white; }}
  .topbar .nav .primary:hover {{ background: #1d4ed8; }}
  .topbar .toggle-sb {{
    background: transparent; border: 1px solid #cbd5e1; border-radius: 5px;
    width: 28px; height: 28px; cursor: pointer; font-size: 14px; color: #475569;
    display: flex; align-items: center; justify-content: center; flex: none;
  }}
  .topbar .toggle-sb:hover {{ background: #f1f5f9; }}
  iframe.show {{ margin-top: 48px; height: calc(100% - 48px); }}

  @media (max-width: 820px) {{
    body {{ grid-template-columns: 1fr; grid-template-rows: auto 1fr; }}
    aside {{ max-height: 240px; }}
    .cover {{ padding: 40px 24px 80px; }}
    .cover h1 {{ font-size: 28px; }}
  }}
</style>
</head>
<body>
<aside>
  <div class="brand">
    <div class="k">대한민국 AI 거점 리더 · 전문인재 과정</div>
    <div class="t">SLM 모델 조사 보고서<br>모음집</div>
    <a class="home" id="home-link">← 발간사로 돌아가기</a>
  </div>
  <ol class="toc">
    {toc_items}
  </ol>
</aside>
<main>
  <div class="topbar" id="topbar">
    <div class="left">
      <button class="toggle-sb" id="toggle-sb" title="목차 접기/펼치기" aria-label="목차 토글">☰</button>
      <div class="title" id="chapter-title"></div>
    </div>
    <div class="nav">
      <a id="open-repo" class="btn" href="#" target="_blank" rel="noopener">GitHub ↗</a>
      <a id="open-fullscreen" class="btn primary" href="#" target="_blank" rel="noopener">전체 화면 ↗</a>
      <button id="prev">← 이전</button>
      <button id="next">다음 →</button>
    </div>
  </div>
  <div id="viewer">
    {cover_html}
  </div>
</main>
<script>
const chapters = {json.dumps(chapters, ensure_ascii=False)};
const coverHTML = document.getElementById('viewer').innerHTML;
const links = Array.from(document.querySelectorAll('ol.toc a'));
const viewer = document.getElementById('viewer');
const topbar = document.getElementById('topbar');
const titleEl = document.getElementById('chapter-title');
const repoLink = document.getElementById('open-repo');
const fullscreenLink = document.getElementById('open-fullscreen');
const prevBtn = document.getElementById('prev');
const nextBtn = document.getElementById('next');
const homeLink = document.getElementById('home-link');
const toggleSb = document.getElementById('toggle-sb');
let current = -1;

function show(i) {{
  if (i < 0 || i >= chapters.length) return;
  current = i;
  const c = chapters[i];
  viewer.innerHTML = `<iframe class="show" src="chapters/${{c.slug}}" title="${{c.org}} ${{c.name}}"></iframe>`;
  topbar.classList.add('show');
  titleEl.textContent = `[${{c.cohort}}기] ${{String(c.n).padStart(2,'0')}}. ${{c.org}} · ${{c.name}}`;
  repoLink.href = c.repo || '#';
  repoLink.style.display = c.repo ? 'inline-flex' : 'none';
  fullscreenLink.href = `chapters/${{c.slug}}`;
  prevBtn.disabled = i === 0;
  nextBtn.disabled = i === chapters.length - 1;
  links.forEach((a) => {{
    const cohort = a.dataset.cohort, n = parseInt(a.dataset.n, 10);
    a.classList.toggle('active', cohort === c.cohort && n === c.n);
  }});
  history.replaceState(null, '', `#c${{c.cohort}}-${{c.n}}`);
}}

function showCover() {{
  current = -1;
  viewer.innerHTML = coverHTML;
  topbar.classList.remove('show');
  links.forEach(a => a.classList.remove('active'));
  history.replaceState(null, '', '#');
}}

links.forEach((a) => {{
  a.addEventListener('click', (ev) => {{
    ev.preventDefault();
    const cohort = a.dataset.cohort;
    const n = parseInt(a.dataset.n, 10);
    const idx = chapters.findIndex(c => c.cohort === cohort && c.n === n);
    if (idx >= 0) show(idx);
  }});
}});
prevBtn.addEventListener('click', () => show(current - 1));
nextBtn.addEventListener('click', () => show(current + 1));
homeLink.addEventListener('click', (ev) => {{ ev.preventDefault(); showCover(); }});
toggleSb.addEventListener('click', () => {{
  document.body.classList.toggle('collapsed');
  try {{ localStorage.setItem('sb-collapsed', document.body.classList.contains('collapsed') ? '1' : '0'); }} catch(e) {{}}
}});
try {{ if (localStorage.getItem('sb-collapsed') === '1') document.body.classList.add('collapsed'); }} catch(e) {{}}
document.addEventListener('keydown', (ev) => {{
  if (ev.key === 'ArrowLeft' && current > 0) show(current - 1);
  if (ev.key === 'ArrowRight' && current >= 0 && current < chapters.length - 1) show(current + 1);
}});

const m = location.hash.match(/^#c(\\d+)-(\\d+)/);
if (m) {{
  const idx = chapters.findIndex(c => c.cohort === m[1] && c.n === parseInt(m[2], 10));
  if (idx >= 0) show(idx);
}}
</script>
</body>
</html>
"""
    (DIST / "index.html").write_text(index_html, encoding="utf-8")
    (DIST / ".nojekyll").write_text("")

    summary = ", ".join(f"{k}기 {v}편" for k, v in sorted(cohort_counts.items()))
    print(f"Built {len(chapters)} chapters ({summary}) → {DIST}/index.html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
