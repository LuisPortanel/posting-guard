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

# Names for an AI reader. Bare "agent" or "assistant" are left out: postings use them for people.
_AI = (r"(?:ai|a\.i\.|llms?|(?:large\s+)?language\s+models?|chat\s*gpt|gpt(?:-?\d\w*)?|claude|gemini|copilot"
       r"|bots?|ai\s+(?:assistants?|agents?|tools?|models?|systems?|screeners?|screening\s+tools?|recruiters?)"
       r"|automated\s+(?:tools?|systems?|agents?|screeners?|screening\s+tools?|application\s+tools?|readers?))")
_AI_ES = (r"(?:ia|inteligencias?\s+artificial(?:es)?|modelos?\s+de\s+lenguaje|bots?"
          r"|(?:asistentes?|agentes?|herramientas?|modelos?)\s+de\s+ia)")
# What an application is made of, for "put X in your cover letter" requests.
_ARTIFACT = (r"(?:cover\s+letter|application|resume|résumé|cv|answers?|responses?|message|e-?mail|subject(?:\s+line)?"
             r"|first\s+line|note|submission|intro(?:duction)?)")
_ARTIFACT_ES = r"(?:carta|solicitud|respuestas?|mensaje|correo|asunto|primera\s+l[ií]nea|postulaci[oó]n|cv)"
_TOKEN = r"[\"“”'‘’«][^\"“”'‘’«»]{2,80}[\"“”'‘’»]"
_CANARY_NOUN = r"(?:(?:code\s*|secret\s*|magic\s*)?words?|phrases?|passcodes?|code\s*names?|keywords?|emojis?|tokens?)"

INSTRUCTION_PATTERNS = [
    ("ai-addressed", re.compile(
        r"\b(if|when)\s+you\s*(?:'re|’re|are)\s+(?:an?\s+)?(?:ai\b|a\.i\.|llm|(?:large\s+)?language\s+model"
        r"|chat\s*gpt|gpt|claude|gemini|copilot|bot\b|automated|ai\s+(?:assistant|agent|tool|model))", re.I)),
    ("ai-addressed", re.compile(
        r"\b(si\s+(?:eres|usted\s+es|es)\s+(?:una?\s+)?(?:ia\b|inteligencia\s+artificial|modelo\s+de\s+lenguaje"
        r"|bot\b|asistente))", re.I)),
    # A note or heading addressed to a model: "Note to language models:", "[AI prompt: ...]".
    ("ai-addressed", re.compile(
        r"\b(?:note|attention|instructions?|message|notice|reminder|warning)\s+(?:to|for)\s+"
        r"(?:all\s+|any\s+)?(?:the\s+)?" + _AI + r"\b"
        r"|\b(?:ai|llm|gpt|chatgpt|claude)\s+(?:prompt|instructions?|note|directive)\s*:"
        r"|^\W*(?:dear|hey|hi|hello|attention)\s+(?:all\s+|any\s+)?" + _AI + r"\s*[:,!]", re.I)),
    ("ai-addressed", re.compile(
        r"\b(?:nota|atenci[oó]n|instrucci[oó]n(?:es)?|mensaje|aviso)\s+(?:para|a)\s+(?:los\s+|las\s+|el\s+|la\s+)?"
        + _AI_ES + r"\b|^\W*para\s+(?:los\s+|las\s+)?" + _AI_ES + r"\s*:", re.I)),
    # A model that reads, screens or applies with this text: "Any LLM processing this text should..."
    ("ai-addressed", re.compile(
        r"\b" + _AI + r"\s+(?:reading|processing|parsing|evaluating|reviewing|screening|summari[sz]ing|analy[sz]ing)"
        r"\s+(?:this|these|the\s+(?:posting|job|role|text|description|listing|ad|page))\b"
        r"|\b" + _AI + r"\s+(?:applying|submitting|filling)\b.{0,40}\bon\s+behalf\s+of\b", re.I)),
    ("ignore-instructions", re.compile(
        r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|prompts?|above|previous|prior|rules)\b"
        r"|\b(ignora|olvida)\b.{0,40}\b(instrucciones|indicaciones|anteriores)\b", re.I)),
    # "Include the word 'pineapple'", "the passcode AEO2026", "your resume must include the exact word X".
    ("canary-phrase", re.compile(
        r"\b(?:include|add|insert|mention|use|write|put|type|start|begin|end|sign|enter|reference)\b.{0,40}"
        r"\b" + _CANARY_NOUN + r"\s*(?::\s*)?(?:" + _TOKEN + r"|(?-i:[A-Z][A-Z0-9-]{2,})\b)"
        r"|\b(?:include|add|insert|mention|use|write|put|type)\b.{0,40}\b" + _CANARY_NOUN + r"\b.{0,60}"
        r"\b(?:in|into|at|on|to|within)\s+(?:the\s+(?:top|start|beginning|end|subject)\s+of\s+)?(?:the\s+|your\s+)" + _ARTIFACT
        + r"|\b(?:your|the)\s+" + _ARTIFACT + r"\s+(?:must|should|needs?\s+to)\s+(?:include|contain|mention|use)\b.{0,30}\b"
        + _CANARY_NOUN + r"\b", re.I)),
    ("canary-phrase", re.compile(
        r"\b(?:incluye|incluya|agrega|agregue|menciona|mencione|escribe|escriba|pon|ponga|usa|use)\b.{0,40}"
        r"\b(?:palabras?|frases?|c[oó]digos?|claves?|emojis?)\b.{0,60}(?:" + _TOKEN + r"|\b(?:en|dentro\s+de)\s+"
        r"(?:el\s+|la\s+|tu\s+|su\s+)" + _ARTIFACT_ES + r")", re.I)),
    # "Tell us your favorite dinosaur in the first line of your application."
    ("canary-phrase", re.compile(
        r"\b(?:mention|include|tell\s+us|write|share|name|list)\b.{0,20}\byour\s+favou?rite\s+\w+\b.{0,40}"
        r"\b(?:in|into|at)\s+(?:the\s+\w+\s+(?:line|sentence)\s+of\s+)?(?:the\s+|your\s+)" + _ARTIFACT
        + r"|\b(?:menciona|incluye|escribe|dinos|cu[eé]ntanos|comparte)\b.{0,20}\btus?\s+\w+\s+favorit[oa]s?\b.{0,40}"
        r"\b(?:en|dentro\s+de)\s+(?:el\s+|la\s+|tu\s+|su\s+)" + _ARTIFACT_ES, re.I)),
    # "Start your cover letter with...", "Begin your message with 'I read it'".
    ("canary-phrase", re.compile(
        r"\b(?:start|begin|open|end|close|sign\s+off|title)\s+(?:your|the)\s+" + _ARTIFACT + r"\s+(?:with|by)\b"
        r"|\b(?:empieza|comienza|inicia|termina)\s+(?:tu|su|la|el)\s+" + _ARTIFACT_ES + r"\s+con\b", re.I)),
    ("canary-phrase", re.compile(
        r"\bso\s+(?:that\s+)?we\s+(?:know|can\s+tell|can\s+see)\s+(?:that\s+)?you(?:'ve|\s+have)?\s+(?:actually\s+)?read\b"
        r"|\bto\s+show\s+(?:us\s+)?(?:that\s+)?you(?:'ve|\s+have)?\s+read\b"
        r"|\bif\s+you(?:'ve|\s+have)?\s+(?:made\s+it|read)\s+(?:this\s+far|to\s+the\s+(?:end|bottom))\b.{0,40}"
        r"\b(?:include|add|mention|write|put|type|use|start|begin)\b"
        r"|\bpara\s+(?:saber|demostrar)\s+que\s+(?:le[ií]ste|ley[oó])\b", re.I)),
    ("canary-phrase", re.compile(r"\b(dad\s+joke|chiste)\b", re.I)),
    ("canary-phrase", re.compile(
        r"\b(include|add|mention|write|put|use|type|incluye|incluya|agrega|agregue|menciona|escribe|pon)\b\s+"
        r"(?:the\s+(?:words?|phrase|title)\s+|la\s+(?:palabra|frase)\s+)?" + _TOKEN + r".{0,20}?\s"
        r"(?:in|into|at|to|en|dentro\s+de)\s+(?:the\s+|your\s+|tu\s+|su\s+|la\s+|el\s+)?"
        r"(?:" + _ARTIFACT + r"|" + _ARTIFACT_ES + r")", re.I)),
    ("ai-addressed", re.compile(
        r"\b(as\s+an\s+ai(?:\s+(?:language\s+model|assistant|model))?\s*[,.:;]"
        r"|you\s+are\s+(?:chatgpt|claude|an?\s+ai(?:\s+(?:language\s+model|assistant|model|agent))?\s*[,.:;!]))",
        re.I)),
    ("off-form-channel", re.compile(
        r"\b(skip|don'?t\s+use|do\s+not\s+use|ignore)\s+the\s+(form|application(?:\s+form)?|portal)\b"
        r"|\b(?:don'?t|do\s+not)\s+apply\s+(?:through|via|on|using)\s+(?:the\s+|our\s+)?(?:portal|form|website|site|ats)\b"
        r"|\b(email|e-mail|write|message|dm)\s+(me|us)\s+directly\b|\bapply\s+(?:only\s+)?(?:by|via|through)\s+e-?mail\b"
        r"|\b(?:send|e-?mail|submit|forward|mail)\b.{0,80}\b(?:resume|résumé|cv|application|portfolio|cover\s+letter)\b"
        r".{0,80}?\b(?:to|at)\s+[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
        r"|\be-?mail\s+[\w.+-]+@[\w-]+(?:\.[\w-]+)+\s+with\b.{0,100}\b(?:resume|cv|cover\s+letter|portfolio)\b"
        r"|\b(?:submit|send|apply)\b.{0,40}\b(?:resume|résumé|cv|application)\b.{0,20}\b(?:through|via|on|over)\s+"
        r"(?:linkedin|telegram|whatsapp|discord|signal|wechat|dm|direct\s+message)\b"
        r"|\bmessage\b.{0,40}\bon\s+(?:telegram|whatsapp|discord|signal|wechat)\b"
        r"|\bno\s+(?:llenes|uses)\s+el\s+formulario\b"
        r"|\b(?:env[ií]a|manda|mándanos|env[ií]anos)\b.{0,40}\b(?:cv|curr[ií]culum|solicitud)\b.{0,40}"
        r"\b(?:a|al|por)\s+(?:[\w.+-]+@[\w-]+(?:\.[\w-]+)+|whatsapp|telegram|linkedin|correo)", re.I)),
]


@dataclass(frozen=True)
class Finding:
    """A line that looks like an instruction. `line` is 1-based within the text it was found in."""
    line: int
    kind: str
    text: str


# Contacts for disability accommodations are not an application channel.
ACCOMMODATION = re.compile(r"\baccommodat|\bajustes?\s+razonables?|\badaptaci[oó]n(?:es)?\s+razonables?", re.I)


def find_instructions(text: str) -> List[Finding]:
    hits = []
    for n, line in enumerate(text.split("\n"), 1):
        for kind, pattern in INSTRUCTION_PATTERNS:
            if kind == "off-form-channel" and ACCOMMODATION.search(line):
                continue
            if pattern.search(line):
                hits.append(Finding(n, kind, line.strip()[:300]))
                break
    return hits
