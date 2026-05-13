#!/usr/bin/env python3
"""각 리포트에서 '선택 모델명' 필드 추출.

대부분의 리포트가 `선택 모델명 <모델>` 형식으로 구조화돼 있어
이를 직접 파싱한다. 결과는 manifest.json 에 'model' 필드로 저장.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifest.json"


def strip_tags(html: str) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def shorten(name: str) -> str:
    """huggingface 경로/긴 식별자를 보기 좋게 단축."""
    name = name.strip(" .·•|—-")
    # owner/model → model (only when looks like HF identifier: no spaces, lowercase-ish)
    if "/" in name and " " not in name and "huggingface.co" not in name:
        name = name.split("/", 1)[1]
    # Drop trailing date suffixes like -2505
    name = re.sub(r"-25\d{2}$", "", name)
    name = re.sub(r"[_]+", "-", name)
    return name.strip()


def extract_model(html: str) -> str:
    text = strip_tags(html)
    # 가장 신뢰성 높은 패턴: "선택 모델명 <X> (Hugging Face 모델 링크|HF|01 모델|<숫자><숫자>)"
    patterns = [
        r"(?:선택|분석)\s*모델명\s+([^\s].{2,120}?)\s+(?:Hugging Face|HF|모델 링크|01 |Hugging|huggingface)",
        r"(?:선택|분석)\s*모델명\s*[:：]?\s*([^\n\r·•|]{3,120})",
        r"Subject\s*Model\s+([A-Za-z0-9._/\- ]{3,80})",
        r"Selected\s+Model\s*[:：]?\s*([A-Za-z0-9._/\- ]{3,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return shorten(m.group(1))
    return ""


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    updated = 0
    for e in manifest:
        if e.get("status") != "ok":
            e["model"] = ""
            continue
        path = ROOT / e["local"]
        html = path.read_text(errors="replace")
        model = extract_model(html)
        e["model"] = model
        print(f"{e['org']:>20s}  {e['name']:>6s}  →  {model or '(미추출)'}")
        if model:
            updated += 1
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\n{updated}/{sum(1 for e in manifest if e.get('status')=='ok')} extracted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
