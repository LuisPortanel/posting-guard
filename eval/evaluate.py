#!/usr/bin/env python3
"""Score posting_guard against the labeled snapshot.

Every posting in the snapshot counts. Postings without a row in `labels.jsonl` were neither flagged
by the guard nor by the broad search in `net.py` and were not in the random sample; they are
counted as negatives. Every posting the guard flags has a label, so precision is exact for this
snapshot. Recall only covers the positives some method found (guard, net, random sample), so the
true recall is lower or equal.

    python eval/evaluate.py --date YYYY-MM-DD [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
if "--src" in sys.argv:                      # score another version: --src path/to/that/src
    sys.path.insert(0, sys.argv[sys.argv.index("--src") + 1])

from posting_guard import scan  # noqa: E402

CATEGORIES = ("hidden-text", "ai-addressed", "read-check", "unicode-trick", "off-form")
KIND_TO_CATEGORY = {
    "ai-addressed": "ai-addressed",
    "ignore-instructions": "ai-addressed",
    "canary-phrase": "read-check",
    "off-form-channel": "off-form",
}


def guard_categories(report) -> set:
    cats = set()
    flags = " ".join(report.flags)
    if "hidden block" in flags or "HTML comment" in flags or "only in hidden" in flags:
        cats.add("hidden-text")
    if "invisible character" in flags or "Unicode tag" in flags or "mixing alphabets" in flags:
        cats.add("unicode-trick")
    for finding in list(report.instructions) + list(report.hidden_instructions):
        cats.add(KIND_TO_CATEGORY.get(finding.kind, finding.kind))
    return cats


def _ratio(a: int, b: int):
    return round(a / b, 3) if b else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--src", help="src directory of the posting_guard version to score")
    a = ap.parse_args(argv)
    postings = {}
    for line in (HERE / "cache" / a.date / "postings.jsonl").open(encoding="utf-8"):
        p = json.loads(line)
        postings[p["id"]] = p
    labels = {}
    for line in (HERE / "labels.jsonl").open(encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            labels[row["id"]] = row
    stale = [i for i, row in labels.items() if i in postings and postings[i]["sha256"] != row["sha256"]]
    if stale:
        print(f"warning: {len(stale)} labeled posting(s) changed since labeling", file=sys.stderr)
    missing = [i for i in labels if i not in postings]

    tp = fp = fn = tn = 0
    per = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CATEGORIES}
    unlabeled_review = []
    errors = []
    for pid, p in postings.items():
        report = scan(p["raw"])
        predicted = guard_categories(report)
        row = labels.get(pid)
        if row is None and report.verdict == "REVIEW":
            unlabeled_review.append(pid)
        truth = set(row["labels"]) if row else set()
        flagged, positive = report.verdict == "REVIEW", bool(truth)
        tp += flagged and positive
        fp += flagged and not positive
        fn += positive and not flagged
        tn += not flagged and not positive
        for c in CATEGORIES:
            per[c]["tp"] += c in predicted and c in truth
            per[c]["fp"] += c in predicted and c not in truth
            per[c]["fn"] += c in truth and c not in predicted
        if flagged != positive:
            errors.append({"id": pid, "type": "FP" if flagged else "FN", "truth": sorted(truth),
                           "guard": sorted(predicted), "note": (row or {}).get("note", "")})

    import posting_guard
    result = {
        "version": posting_guard.__version__,
        "snapshot": a.date,
        "postings": len(postings),
        "boards": len({p["board"] for p in postings.values()}),
        "labeled": sum(1 for i in labels if i in postings),
        "positives": tp + fn,
        "guard_review": tp + fp,
        "posting_level": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                          "precision": _ratio(tp, tp + fp), "recall_on_found": _ratio(tp, tp + fn)},
        "per_category": {c: {**v, "precision": _ratio(v["tp"], v["tp"] + v["fp"]),
                             "recall_on_found": _ratio(v["tp"], v["tp"] + v["fn"])}
                         for c, v in per.items()},
        "errors": errors,
        "unlabeled_review": unlabeled_review,
        "labels_not_in_snapshot": missing,
    }
    if a.json:
        print(json.dumps(result, indent=1))
    else:
        pl = result["posting_level"]
        print(f"posting-guard {result['version']}, snapshot {a.date}: {result['postings']} postings from {result['boards']} boards, "
              f"{result['labeled']} labeled, {result['positives']} positive")
        print(f"posting level: precision {pl['precision']} recall-on-found {pl['recall_on_found']} "
              f"(tp {tp} fp {fp} fn {fn})")
        for c, v in result["per_category"].items():
            print(f"  {c:14s} precision {v['precision']} recall-on-found {v['recall_on_found']} "
                  f"(tp {v['tp']} fp {v['fp']} fn {v['fn']})")
        if unlabeled_review:
            print(f"warning: {len(unlabeled_review)} REVIEW posting(s) have no label", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
