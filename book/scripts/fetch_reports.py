#!/usr/bin/env python3
"""각 저장소를 얕게 clone하여 SLM 리포트 HTML을 수집."""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORS_TSV = ROOT / "data" / "authors.tsv"
REPORTS_DIR = ROOT / "reports"
MANIFEST = ROOT / "data" / "manifest.json"


def parse_repo(url: str) -> tuple[str, str] | None:
    if not url:
        return None
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url.strip())
    if not m:
        return None
    return m.group(1), m.group(2)


def pick_html(root: Path) -> Path | None:
    htmls = [p for p in root.rglob("*.html") if ".git" not in p.parts]
    if not htmls:
        return None

    def score(p: Path):
        rel = p.relative_to(root).as_posix()
        return (
            "slm_report" not in rel.lower(),
            "report" not in rel.lower(),
            rel.count("/"),
            -len(rel),
        )

    htmls.sort(key=score)
    return htmls[0]


def safe_slug(s: str) -> str:
    return re.sub(r"[^\w가-힣\-]+", "_", s).strip("_")


def clone(url: str, dest: Path) -> bool:
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return True
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"  clone failed: {e.stderr.decode(errors='replace')[:200]}\n")
        return False


def main() -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    with AUTHORS_TSV.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            name = row["name"].strip()
            org = row["org"].strip()
            cohort = (row.get("cohort") or "1").strip()
            repo_url = (row.get("repo") or "").strip()
            pages_url = (row.get("pages_url") or "").strip()
            entry = {
                "cohort": cohort,
                "name": name,
                "org": org,
                "repo": repo_url,
                "pages_url": pages_url,
            }
            print(f"\n[ {org} / {name} ]")
            if not repo_url:
                print("  (no repo URL — skipped)")
                entry["status"] = "missing-url"
                manifest.append(entry)
                continue
            parsed = parse_repo(repo_url)
            if not parsed:
                entry["status"] = "bad-url"
                manifest.append(entry)
                continue
            owner, repo = parsed
            entry["owner"], entry["repo_name"] = owner, repo
            clone_url = f"https://github.com/{owner}/{repo}.git"
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td) / "repo"
                if not clone(clone_url, td_path):
                    entry["status"] = "clone-failed"
                    manifest.append(entry)
                    continue
                html = pick_html(td_path)
                if not html:
                    print("  (no HTML in repo)")
                    entry["status"] = "no-html"
                    manifest.append(entry)
                    continue
                cohort_dir = REPORTS_DIR / f"cohort{cohort}"
                cohort_dir.mkdir(parents=True, exist_ok=True)
                dest = cohort_dir / f"{safe_slug(org)}_{safe_slug(name)}.html"
                shutil.copy2(html, dest)
                entry["html_path"] = html.relative_to(td_path).as_posix()
                entry["local"] = str(dest.relative_to(ROOT))
                entry["bytes"] = dest.stat().st_size
                entry["status"] = "ok"
                print(f"  -> {dest.name} ({entry['bytes']:,} bytes) from {entry['html_path']}")
            manifest.append(entry)

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    ok = sum(1 for e in manifest if e.get("status") == "ok")
    print(f"\n=== {ok}/{len(manifest)} downloaded ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
