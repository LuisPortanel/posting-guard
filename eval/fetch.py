#!/usr/bin/env python3
"""Download a snapshot of public job postings for the evaluation set.

Reads `eval/boards.txt` (one `ats:board` per line, ats = greenhouse | lever | ashby) and calls each
ATS's public job board API: one request per board, one second apart. Keeps at most `--per-board`
postings per board, picked by a stable hash of the posting id, so large employers do not dominate.

Writes `eval/cache/<date>/postings.jsonl`. The cache is not committed: postings belong to their
employers, and the committed labels refer to them by id and content hash only.

    python eval/fetch.py [--per-board 40] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = "posting-guard-eval/0.2 (+https://github.com/LuisPortanel/posting-guard; research, one request per board)"
API = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{board}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{board}",
}


def _lever_html(job: dict) -> str:
    parts = [job.get("description") or ""]
    for block in job.get("lists") or []:
        parts.append("<h3>%s</h3><ul>%s</ul>" % (block.get("text") or "", block.get("content") or ""))
    parts.append(job.get("additional") or "")
    return "\n".join(parts)


def normalize(ats: str, board: str, data) -> list:
    if ats == "greenhouse":
        jobs = [(str(j["id"]), j.get("title"), j.get("absolute_url"), j.get("content") or "")
                for j in data.get("jobs") or []]
    elif ats == "lever":
        jobs = [(j["id"], j.get("text"), j.get("hostedUrl"), _lever_html(j)) for j in data or []]
    else:
        jobs = [(j["id"], j.get("title"), j.get("jobUrl"), j.get("descriptionHtml") or "")
                for j in data.get("jobs") or [] if j.get("isListed", True)]
    out = []
    for job_id, title, url, body in jobs:
        if not body.strip():
            continue
        out.append({
            "id": f"{ats}:{board}:{job_id}",
            "ats": ats,
            "board": board,
            "title": title or "",
            "url": url or "",
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "raw": body,
        })
    return out


def pick(postings: list, n: int) -> list:
    return sorted(postings, key=lambda p: hashlib.sha256(p["id"].encode()).hexdigest())[:n]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-board", type=int, default=40)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    a = ap.parse_args(argv)
    boards = [line.strip() for line in (HERE / "boards.txt").read_text().splitlines()
              if line.strip() and not line.startswith("#")]
    out_dir = HERE / "cache" / a.date
    out_dir.mkdir(parents=True, exist_ok=True)
    total, failed = 0, []
    with open(out_dir / "postings.jsonl", "w", encoding="utf-8") as f:
        for i, entry in enumerate(boards, 1):
            ats, board = entry.split(":", 1)
            req = urllib.request.Request(API[ats].format(board=board),
                                         headers={"User-Agent": UA, "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.load(r)
            except (urllib.error.URLError, ValueError, TimeoutError) as e:
                failed.append(f"{entry}: {e}")
                time.sleep(1)
                continue
            chosen = pick(normalize(ats, board, data), a.per_board)
            for p in chosen:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
            total += len(chosen)
            print(f"[{i}/{len(boards)}] {entry}: {len(chosen)}", file=sys.stderr)
            time.sleep(1)
    (out_dir / "fetch.log").write_text(
        f"date {a.date}\nboards {len(boards)}\npostings {total}\nfailed {len(failed)}\n" + "\n".join(failed) + "\n")
    print(f"{total} postings from {len(boards) - len(failed)} boards ({len(failed)} failed) -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
