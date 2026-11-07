"""Line patterns that look like instructions aimed at an AI model or at the applicant's tooling.
English and Spanish."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

# Words that make hidden text or an HTML comment worth reporting.
SUSPICIOUS = re.compile(
    r"\b(ai|a\.i\.|llm|gpt|chatgpt|claude|gemini|bot|model|prompt|candidate|applicant|resume|cv|recruiter"
    r"|ignore|rank|score|hire|hiring|instructions?|ia|candidato|modelo)\b", re.I)

INSTRUCTION_PATTERNS = [
    ("ai-addressed", re.compile(
        r"\b(if|when)\s+you\s*(?:'re|’re|are)\s+(?:an?\s+)?(?:ai\b|a\.i\.|llm|(?:large\s+)?language\s+model"
        r"|chat\s*gpt|gpt|claude|gemini|copilot|bot\b|automated|ai\s+(?:assistant|agent|tool|model))", re.I)),
    ("ai-addressed", re.compile(
        r"\b(si\s+(?:eres|usted\s+es|es)\s+(?:una?\s+)?(?:ia\b|inteligencia\s+artificial|modelo\s+de\s+lenguaje"
        r"|bot\b|asistente))", re.I)),
    ("ignore-instructions", re.compile(
        r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|prompts?|above|previous|prior|rules)\b"
        r"|\b(ignora|olvida)\b.{0,40}\b(instrucciones|indicaciones|anteriores)\b", re.I)),
    ("canary-phrase", re.compile(
        r"\b(include|add|insert|mention|use|write|put|type|start|begin|end|sign)\b.{0,50}"
        r"\b(word|phrase|code\s*word|keyword|password|emoji|joke|haiku|poem|token|secret)\b"
        r"|\b(incluye|incluya|agrega|agregue|menciona|mencione|escribe|escriba|pon|ponga)\b.{0,50}"
        r"\b(palabra|frase|c[oó]digo|clave|chiste|emoji)\b", re.I)),
    ("canary-phrase", re.compile(
        r"\bso\s+(?:that\s+)?we\s+(?:know|can\s+tell|can\s+see)\s+(?:that\s+)?you(?:'ve|\s+have)?\s+(?:actually\s+)?read\b"
        r"|\bto\s+show\s+(?:us\s+)?(?:that\s+)?you\s+read\b"
        r"|\bpara\s+saber\s+que\s+(?:le[ií]ste|ley[oó])\b", re.I)),
    ("canary-phrase", re.compile(r"\b(dad\s+joke|chiste)\b", re.I)),
    ("canary-phrase", re.compile(
        r"\b(include|add|mention|write|put|use|type|incluye|incluya|agrega|agregue|menciona|escribe|pon)\b\s+"
        r"(?:the\s+(?:words?|phrase|title)\s+|la\s+(?:palabra|frase)\s+)?"
        r"[\"“”'‘’«][^\"“”'‘’«»]{2,80}[\"“”'‘’»]\s+(?:in|into|at|to|en|dentro\s+de)\s+"
        r"(?:the\s+|your\s+|tu\s+|su\s+|la\s+|el\s+)?"
        r"(?:cover\s+letter|application|answer|message|e-?mail|subject|first\s+line|carta|solicitud|respuesta"
        r"|mensaje|correo|asunto)", re.I)),
    ("ai-addressed", re.compile(
        r"\b(system\s+prompt|as\s+an\s+ai(?:\s+(?:language\s+model|assistant|model))?\s*[,.:;]"
        r"|you\s+are\s+(?:chatgpt|claude|an?\s+ai(?:\s+(?:language\s+model|assistant|model|agent))?\s*[,.:;!]))",
        re.I)),
    ("off-form-channel", re.compile(
        r"\b(skip|don'?t\s+use|do\s+not\s+use|ignore)\s+the\s+(form|application(?:\s+form)?)\b"
        r"|\b(email|e-mail|write|message|dm)\s+(me|us)\s+directly\b|\bapply\s+(?:only\s+)?(?:by|via|through)\s+e-?mail\b"
        r"|\bno\s+(?:llenes|uses)\s+el\s+formulario\b", re.I)),
]


@dataclass(frozen=True)
class Finding:
    """A line that looks like an instruction. `line` is 1-based within the text it was found in."""
    line: int
    kind: str
    text: str


def find_instructions(text: str) -> List[Finding]:
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        for kind, pattern in INSTRUCTION_PATTERNS:
            if pattern.search(line):
                hits.append(Finding(n, kind, line.strip()[:300]))
                break
    return hits
