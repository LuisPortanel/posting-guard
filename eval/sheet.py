#!/usr/bin/env python3
"""Build the labeling sheet for a snapshot.

A posting becomes a candidate for labeling when posting_guard says REVIEW, when it has minor hidden
text the guard chose to ignore, or when the independent broad search in `net.py` finds anything.
A fixed-seed random sample of the remaining postings is added, so misses outside both nets can show
up too.

Writes, next to the snapshot (not committed, it quotes posting text):
  candidates.md   evidence per candidate, for a human to label
  sample.txt      ids of the random sample

    python eval/sheet.py [--date YYYY-MM-DD] [--sample 60]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from posting_guard import scan  # noqa: E402
from net import scan_net  # noqa: E402


def load(date: str) -> list:
    path = HERE / "cache" / date / "postings.jsonl"
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True)
    ap.add_argument("--sample", type=int, default=60)
    a = ap.parse_args(argv)
    postings = load(a.date)
    out = HERE / "cache" / a.date
    cands, rest = [], []
    for p in postings:
        r = scan(p["raw"])
        net = scan_net(p["raw"])
        if r.verdict == "REVIEW" or r.minor_hidden_text or net:
            cands.append((p, r, net))
        else:
            rest.append(p)
    rng = random.Random(20261107)
    sample = rng.sample(rest, min(a.sample, len(rest)))
    (out / "sample.txt").write_text("".join(p["id"] + "\n" for p in sample))
    with open(out / "candidates.md", "w", encoding="utf-8") as f:
        for p, r, net in cands:
            f.write(f"## {p['id']}\n{p['title']} | {p['url']}\n")
            f.write(f"guard: {r.summary}\n")
            for fnd in r.instructions:
                f.write(f"  G> line {fnd.line} ({fnd.kind}): {fnd.text[:240]}\n")
            for fnd in r.hidden_instructions:
                f.write(f"  G> HIDDEN ({fnd.kind}): {fnd.text[:240]}\n")
            if r.hidden_text:
                f.write(f"  G hidden: {r.hidden_text[:300]!r}\n")
            if r.minor_hidden_text:
                f.write(f"  G minor hidden: {r.minor_hidden_text[:200]!r}\n")
            for c in r.suspicious_comments:
                f.write(f"  G comment: {c[:200]!r}\n")
            if r.invisible_chars:
                f.write(f"  G invisible: {r.invisible_chars} inside-words={r.invisible_inside_words}\n")
            for s in r.tag_smuggled_text:
                f.write(f"  G tag-smuggled: {s[:200]!r}\n")
            if r.mixed_script_words:
                f.write(f"  G mixed: {r.mixed_script_words[:5]}\n")
            for u in r.hidden_only_urls:
                f.write(f"  G hidden-url: {u[:160]}\n")
            for cat, snip in net[:8]:
                f.write(f"  N [{cat}] {snip}\n")
            if len(net) > 8:
                f.write(f"  N ... {len(net) - 8} more\n")
            f.write("\n")
    review = sum(1 for _, r, _ in cands if r.verdict == "REVIEW")
    print(f"{len(postings)} postings | candidates {len(cands)} (guard REVIEW {review}) | sample {len(sample)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
