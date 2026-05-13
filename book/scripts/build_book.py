#!/usr/bin/env python3
"""manifest.json + reports/*.html → dist/ 책자 생성.

- chapters/ : 원본 HTML을 그대로 복사 (iframe으로 로드)
- index.html : 사이드바 목차 + 메인 iframe 뷰어
"""
from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.json"
REPORTS = ROOT / "reports"
DIST = ROOT / "dist"
CHAPTERS = DIST / "chapters"

# 정렬용 한국어 가나다 키 (간단히 문자열 정렬로 충분)
def sort_key(e: dict) -> tuple:
    return (e["org"], e["name"])


def safe_slug(s: str) -> str:
    return re.sub(r"[^\w가-힣\-]+", "_", s).strip("_")


def main() -> int:
    entries = json.loads(MANIFEST.read_text())
    ok = [e for e in entries if e.get("status") == "ok"]
    missing = [e for e in entries if e.get("status") != "ok"]
    ok.sort(key=sort_key)

    if DIST.exists():
        shutil.rmtree(DIST)
    CHAPTERS.mkdir(parents=True)

    chapters = []
    for i, e in enumerate(ok, 1):
        src = ROOT / e["local"]
        slug = f"{i:02d}_{safe_slug(e['org'])}_{safe_slug(e['name'])}.html"
        dst = CHAPTERS / slug
        shutil.copy2(src, dst)
        chapters.append({
            "n": i,
            "slug": slug,
            "name": e["name"],
            "org": e["org"],
            "repo": e.get("repo", ""),
        })

    toc_items = "\n".join(
        f'<li><a href="#" data-src="chapters/{c["slug"]}" data-n="{c["n"]}">'
        f'<span class="num">{c["n"]:02d}</span>'
        f'<span class="meta"><span class="org">{escape(c["org"])}</span>'
        f'<span class="name">{escape(c["name"])}</span></span></a></li>'
        for c in chapters
    )

    missing_items = (
        "<h3>수집되지 않은 항목</h3><ul class='missing'>"
        + "".join(
            f"<li>{escape(m['org'])} / {escape(m['name'])} — <code>{escape(m.get('status',''))}</code></li>"
            for m in missing
        )
        + "</ul>"
        if missing
        else ""
    )

    cover_html = (
        '<div class="cover">'
        '<div class="kicker">AI 전문인재 과정</div>'
        '<h1>SLM 모델 조사 보고서 모음집</h1>'
        '<p class="lede">1일차 과제 · 24명의 공공부문 수강생이 작성한 SLM 모델 조사 보고서를 한 권으로 엮었습니다.</p>'
        f'<p class="stats">총 <strong>{len(chapters)}</strong>편 · '
        f'소속 기관 가나다순 정렬</p>'
        '<p class="hint">← 왼쪽 목차에서 챕터를 선택하세요.</p>'
        f'{missing_items}'
        '</div>'
    )

    index_html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>SLM 모델 조사 보고서 모음집</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.css" rel="stylesheet">
<style>
  :root {{
    --bg:#0f172a; --panel:#111827; --panel-2:#1f2937;
    --ink:#e5e7eb; --ink-mute:#94a3b8; --accent:#60a5fa; --accent-soft:#1e3a8a;
    --border:#1f2937;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    font-family: 'Pretendard Variable','Pretendard','Inter','Noto Sans KR',sans-serif;
    background: var(--bg); color: var(--ink);
    display: grid; grid-template-columns: 320px 1fr; height: 100vh;
  }}
  aside {{
    background: var(--panel);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    display: flex; flex-direction: column;
  }}
  .brand {{
    padding: 20px 20px 12px;
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; background: var(--panel); z-index: 1;
  }}
  .brand .k {{ font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-mute); }}
  .brand .t {{ font-weight: 800; font-size: 17px; margin-top: 4px; line-height: 1.3; }}
  .brand a {{ color: var(--accent); text-decoration: none; font-size: 12px; }}
  ol.toc {{ list-style: none; padding: 8px 0; margin: 0; }}
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
  iframe {{
    width: 100%; height: 100%; border: 0; background: white;
  }}
  .cover {{
    height: 100%; overflow-y: auto; padding: 80px 60px;
    color: #0f172a; background: linear-gradient(180deg,#f8fafc, #e2e8f0);
    max-width: 880px; margin: 0 auto;
  }}
  .cover .kicker {{ font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: #475569; font-weight: 700; }}
  .cover h1 {{ font-size: 44px; margin: 12px 0 16px; line-height: 1.15; letter-spacing: -0.02em; }}
  .cover .lede {{ font-size: 17px; color: #334155; line-height: 1.7; max-width: 640px; }}
  .cover .stats {{ margin-top: 24px; font-size: 14px; color: #475569; }}
  .cover .hint {{ margin-top: 40px; padding: 12px 16px; background: #fff; border-left: 3px solid #2563eb; border-radius: 4px; font-size: 14px; color: #1e3a8a; }}
  .cover h3 {{ margin-top: 48px; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; }}
  .cover .missing {{ margin: 8px 0 0; padding-left: 20px; font-size: 13px; color: #64748b; }}
  .cover .missing code {{ background: #e2e8f0; padding: 1px 6px; border-radius: 3px; font-size: 11px; }}
  .topbar {{
    position: absolute; top: 0; left: 0; right: 0; height: 44px;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 16px; background: rgba(255,255,255,0.95); backdrop-filter: blur(8px);
    border-bottom: 1px solid #e2e8f0; font-size: 13px; color: #334155; z-index: 5;
    display: none;
  }}
  .topbar.show {{ display: flex; }}
  .topbar .title {{ font-weight: 600; }}
  .topbar .nav button {{
    background: white; border: 1px solid #cbd5e1; padding: 4px 10px; border-radius: 4px;
    cursor: pointer; margin-left: 6px; font-size: 12px;
  }}
  .topbar .nav button:hover {{ background: #f1f5f9; }}
  .topbar .nav button:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .topbar a {{ color: #2563eb; text-decoration: none; font-size: 12px; margin-left: 12px; }}
  iframe.show {{ margin-top: 44px; height: calc(100% - 44px); }}
  @media (max-width: 820px) {{
    body {{ grid-template-columns: 1fr; grid-template-rows: auto 1fr; }}
    aside {{ max-height: 220px; }}
  }}
</style>
</head>
<body>
<aside>
  <div class="brand">
    <div class="k">AI 전문인재 과정 · 1일차</div>
    <div class="t">SLM 모델 조사 보고서<br>모음집</div>
  </div>
  <ol class="toc">
    {toc_items}
  </ol>
</aside>
<main>
  <div class="topbar" id="topbar">
    <div class="title" id="chapter-title"></div>
    <div class="nav">
      <a id="open-repo" href="#" target="_blank" rel="noopener">GitHub ↗</a>
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
const links = Array.from(document.querySelectorAll('ol.toc a'));
const viewer = document.getElementById('viewer');
const topbar = document.getElementById('topbar');
const titleEl = document.getElementById('chapter-title');
const repoLink = document.getElementById('open-repo');
const prevBtn = document.getElementById('prev');
const nextBtn = document.getElementById('next');
let current = -1;

function show(i) {{
  if (i < 0 || i >= chapters.length) return;
  current = i;
  const c = chapters[i];
  viewer.innerHTML = `<iframe class="show" src="chapters/${{c.slug}}" title="${{c.org}} ${{c.name}}"></iframe>`;
  topbar.classList.add('show');
  titleEl.textContent = `${{String(c.n).padStart(2,'0')}}. ${{c.org}} · ${{c.name}}`;
  repoLink.href = c.repo || '#';
  repoLink.style.display = c.repo ? 'inline' : 'none';
  prevBtn.disabled = i === 0;
  nextBtn.disabled = i === chapters.length - 1;
  links.forEach((a, idx) => a.classList.toggle('active', idx === i));
  history.replaceState(null, '', `#${{c.n}}`);
}}

links.forEach((a, idx) => {{
  a.addEventListener('click', (ev) => {{ ev.preventDefault(); show(idx); }});
}});
prevBtn.addEventListener('click', () => show(current - 1));
nextBtn.addEventListener('click', () => show(current + 1));
document.addEventListener('keydown', (ev) => {{
  if (ev.key === 'ArrowLeft' && current > 0) show(current - 1);
  if (ev.key === 'ArrowRight' && current < chapters.length - 1) show(current + 1);
}});

const m = location.hash.match(/^#(\\d+)/);
if (m) {{
  const n = parseInt(m[1], 10);
  const idx = chapters.findIndex(c => c.n === n);
  if (idx >= 0) show(idx);
}}
</script>
</body>
</html>
"""
    (DIST / "index.html").write_text(index_html, encoding="utf-8")

    # .nojekyll for GitHub Pages (paths with Korean chars must pass through)
    (DIST / ".nojekyll").write_text("")

    print(f"Built {len(chapters)} chapters → {DIST}/index.html")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
