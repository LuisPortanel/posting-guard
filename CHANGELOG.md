# Changelog

## 0.2.0 (2026-11-07)

Changes driven by the first evaluation (`eval/`, snapshot of 10,439 public postings, 2026-11-06).

Detection added:
- White text written as `rgb(255, 255, 255)`, `hsl(0 0% 100%)` or near-white (every channel 245 or
  more), and colors with alpha below 0.05. `transform: scale(0)`.
- Notes and headings addressed to a model ("Note to language models:", "[AI prompt: ...]",
  "Attention automated tools:"), a model "processing this text", AI agents "applying on behalf of"
  someone; Spanish equivalents.
- Read checks: a passcode or capitalized code word, "your resume must include the exact word",
  "your favorite X in the first line of your application", "begin your message with".
- Requests to apply outside the form: send the resume to an email address, submit it through
  LinkedIn or a messaging app, "do not apply through the portal".
- Instructions disguised with Cyrillic or Greek look-alike letters (patterns run on a Latin skeleton).
- Hidden text of 4 or more words (was 8), so a single hidden fake requirement is reported.

False positives removed:
- "Microsoft Word", "word processing", "keyword strategy": the read-check pattern now needs a quoted
  or capitalized token, or a place in the application ("in your cover letter").
- "system prompts" as a job skill; "set the direction for AI".
- Zero-width spaces next to tags and punctuation (editor output), soft hyphens, bidi marks in
  right-to-left text: counted, no longer flagged. Flagged: invisibles inside Latin words, tag
  characters, bidi overrides and isolates, runs of variation selectors.
- A single word mixing alphabets (usually a keyboard-layout slip, such as one Latin letter in a
  Ukrainian word): reported, not flagged. Two or more Latin words with look-alike letters are flagged.
- Hashtags in hidden text (LinkedIn's `#LI-Remote` codes, SEO tag lists) do not count as words.
- White text on a dark background set in the same style is visible.
- Contacts for disability accommodations are not an off-form channel.

## 0.1.0 (2026-11-06)

- First release: `scan()` API, `posting-guard` command line, tests.
