# Evaluation

How well does `posting-guard` do on real job postings? This folder holds a labeled snapshot of
public postings and the scripts that score the guard against it.

## The snapshot

- `boards.txt` lists public job boards on Greenhouse, Lever and Ashby. They were taken from
  [freehire.me](https://freehire.me) search results across job families (engineering, sales, design,
  data, support and others), not chosen for having traps.
- `fetch.py` downloads every board through its public job board API, one request per board, and keeps
  at most 40 postings per board, picked by a stable hash so large employers do not dominate.
- The postings themselves are **not** in this repository: they belong to their employers.
  `labels.jsonl` refers to each one by id (`ats:board:job_id`) and the SHA-256 of its content.
  Postings close over time, so a later download will not match the snapshot exactly; `evaluate.py`
  warns about labels whose posting changed or disappeared.

## Labels

Each labeled posting gets zero or more of these categories. They describe what the posting
contains, not whether its author meant harm.

| Label | The posting contains |
|---|---|
| `hidden-text` | meaningful text a human reader of the rendered page does not see: a hidden element or an HTML comment addressed to a reader. Short accessibility labels ("opens in a new tab") and empty template elements do not count. |
| `ai-addressed` | text addressed to an AI system or automated tool ("If you are an LLM...", "Note to AI screeners..."). Policies addressed to people about AI ("please don't use ChatGPT to write your answers") do not count. |
| `read-check` | a request to put a specific word, phrase, emoji or answer in the application to show the posting was read. |
| `unicode-trick` | text hidden in Unicode tag characters, zero-width characters inside words, bidi controls that reorder text, or words that mix Latin with look-alike Cyrillic or Greek letters. |
| `off-form` | a request to skip the application form or to apply through another channel (email, DM, messaging apps). |

A posting is **positive** when it has at least one label.

## How postings were picked for labeling

1. Every posting the guard flags as `REVIEW`.
2. Every posting with short hidden text that the guard chose to ignore.
3. Every posting that `net.py` matches. `net.py` is a deliberately broad search written separately
   from the guard's rules, so it can find what the guard misses. It is noisy on purpose.
4. A fixed-seed random sample of 60 of the remaining postings, read in full.

Everything else is counted as negative. Because every `REVIEW` posting is labeled, precision is exact
for this snapshot. Recall can only count the positives that one of the four methods found, so it is
reported as *recall on found positives*, an upper bound on the real recall.

`inject.py` adds a second, synthetic measure: it plants known traps (visible lines in English and
Spanish, 15 ways of hiding text, 4 Unicode tricks) into postings the guard calls clean, and counts how
many the guard catches.

## Running it

```
python eval/fetch.py --date 2026-11-06          # downloads into eval/cache/ (not committed)
python eval/sheet.py --date 2026-11-06          # evidence for labeling
python eval/evaluate.py --date 2026-11-06
python eval/inject.py --date 2026-11-06
```

`--src` scores another version, for example 0.1.0:

```
git worktree add ../posting-guard-0.1.0 v0.1.0
python eval/evaluate.py --date 2026-11-06 --src ../posting-guard-0.1.0/src
```

## Who labeled

First pass by Claude (Anthropic's model), reading the evidence the sheet prints for each candidate;
the random sample was read in full by two separate Claude subagents. Cases marked doubtful are decided
by the maintainer. The `by` field of each label says who set it.

## Results

Snapshot of 2026-11-06: 10,439 postings from 355 boards. 1,988 were labeled: every candidate from the
four methods above, plus every posting 0.2.0 flags. 28 are positive, from 11 employers.

| | 0.1.0 | 0.2.0 |
|---|---|---|
| Postings flagged `REVIEW` | 97 | 70 |
| True positives | 5 | 28 |
| False positives | 92 (23 employers) | 42 (3 employers) |
| Missed positives | 23 (7 employers) | 0 |
| **Precision** | **5%** | **40%** |
| **Recall on found positives** | **18%** | **100%** |
| Planted traps caught (`inject.py`, 44 kinds) | 30 | 44 |

By category (true positives / false positives / misses):

| Category | 0.1.0 | 0.2.0 |
|---|---|---|
| `hidden-text` | 0 / 0 / 4 | 4 / 2 / 0 |
| `ai-addressed` | 1 / 4 / 1 | 2 / 0 / 0 |
| `read-check` | 3 / 13 / 0 | 3 / 0 / 0 |
| `unicode-trick` | 0 / 76 / 0 | 0 / 0 / 0 |
| `off-form` | 0 / 0 / 20 | 20 / 40 / 0 |

How to read this:

- **0.1.0 was mostly noise.** 61 of its 92 false positives came from two employers: zero-width spaces
  that an editor left next to tags (one Brazilian bank, 39 postings) and Ukrainian text with one Latin
  letter in a Cyrillic word (22 postings). The rest were "Microsoft Word" read as a code word,
  "system prompts" as a job skill, soft hyphens, and "ΔE" (a color-difference unit).
- **It also missed the clearest trap in the snapshot:** an instruction to AI resume generators in white
  8pt text, written as `color: rgb(255, 255, 255)`, which 0.1.0 did not recognize as white. A hidden
  requirement for a framework that does not exist (a likely canary for AI-written resumes) was missed
  for the same reason.
- **0.2.0's false positives are almost all one decision.** 40 of the 42 are one employer's boilerplate:
  "should you prefer to opt out of the automated evaluation, please submit your application directly to"
  an email address. It is labeled negative for now and marked doubtful (see below); counted as positive,
  0.2.0's precision would be 97% (68 of 70).
- **These 0.2.0 numbers are optimistic.** Its rules were revised after reading this snapshot's errors,
  and the planted traps were in view while writing them. They show the fixes work on the cases that
  motivated them, not how the rules do on new postings. The next step is a second snapshot, labeled the
  same way, and planted phrasings written by someone else.
- Real traps are rare: 28 positives in 10,439 postings, and only 8 of them (from 6 employers) are hidden
  text, text aimed at a model, or read checks. The other 20 ask to apply by email or LinkedIn.
- The 60 randomly sampled postings had no positives. Zero in 60 only bounds the share of positives among
  the 8,451 postings no method flagged at about 5% (95% confidence): a weak bound, given how rare
  positives are.

### Doubtful labels

46 labels are marked `"doubtful": true` and wait for the maintainer's decision; the numbers above use
the provisional labels.

| Postings | Case | Provisional label |
|---|---|---|
| 40 (one employer) | email the application to opt out of automated evaluation | negative |
| 5 (one employer) | white text with long hashtag lists (#London #Paris ...) | negative |
| 1 (same employer) | white text with hashtags and a long list of plain keywords (SQL, Java, machine learning...) | `hidden-text` |
