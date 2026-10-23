"""Small dependency-free CV parser used by Component 4 upload handling."""

from __future__ import annotations

import re
import zipfile
from collections.abc import Mapping
from io import BytesIO
from typing import Any
from xml.etree import ElementTree


_SKILLS = (
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "SQL", "R",
    "HTML", "CSS", "React", "Angular", "Vue", "Node.js", "Django", "Flask",
    "FastAPI", "Spring Boot", " .NET", "PHP", "Laravel", "AWS", "Azure", "GCP",
    "Docker", "Kubernetes", "Terraform", "Git", "GitHub", "PostgreSQL", "MySQL",
    "MongoDB", "Redis", "Pandas", "NumPy", "PyTorch", "TensorFlow", "Scikit-learn",
    "Machine Learning", "Deep Learning", "NLP", "Power BI", "Tableau", "Selenium",
)


def _clean(value: str) -> str:
    return " ".join(value.split()).strip()


def _extract_docx(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    # One line per paragraph so _section() can recognise headings.
    paragraphs = [
        _clean("".join(node.text or "" for node in para.iter() if node.tag.endswith("}t")))
        for para in root.iter()
        if para.tag.endswith("}p")
    ]
    return "\n".join(p for p in paragraphs if p)


def _readable(chunk: str) -> bool:
    """True for text-like chunks; rejects bytes from compressed PDF streams."""
    if not chunk or not re.search(r"[A-Za-z]{2}", chunk):
        return False
    printable = sum(1 for ch in chunk if ch.isprintable() and ord(ch) < 0x250)
    return printable / len(chunk) >= 0.95


def _extract_pdf(data: bytes) -> str:
    # Most PDFs (Canva, Word, LaTeX exports) store text in compressed streams,
    # so reading the raw bytes yields binary noise; pypdf decodes them.
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None
    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            # Keep line breaks so _section() can find headings.
            text = "\n".join(
                " ".join(line.split()) for page in pages for line in page.splitlines()
            ).strip()
            if text:
                return text
        except Exception:
            pass
    decoded = data.decode("latin-1", errors="ignore")
    chunks = [chunk for chunk in re.findall(r"\(([^()]*)\)", decoded) if _readable(chunk)]
    return _clean(" ".join(chunks))


def _extract_text(filename: str, data: bytes) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".docx"):
        return _extract_docx(data)
    if lower_name.endswith(".pdf"):
        return _extract_pdf(data)
    return _clean(data.decode("utf-8", errors="ignore"))


_SECTION_NAMES = {
    "qualifications": ("summary", "profile", "qualifications", "professional summary", "objective"),
    "certifications": ("certifications", "certificates", "licenses & certifications"),
    "education": ("education", "academic background", "education & qualifications"),
    "projects": ("projects", "project experience", "academic projects", "undergraduate projects"),
    "work_experience": ("experience", "work experience", "employment", "professional experience", "internships"),
}
# Headings that end a section but are not mapped to a CV field.  "About me"
# is excluded from qualifications: templates often put contact details there.
_OTHER_HEADINGS = (
    "about me", "skills", "technical skills", "soft skills", "contact", "languages", "references",
    "interests", "hobbies", "achievements", "awards", "volunteering", "personal details",
)
_ALL_HEADINGS = {name for names in _SECTION_NAMES.values() for name in names} | set(_OTHER_HEADINGS)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<![\w/])\+?\d[\d\s()-]{7,}\d(?![\w/])")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def _redact(text: str) -> str:
    """Drop contact details; matching never needs them and they reach the LLM."""
    text = _EMAIL_RE.sub("", text)
    text = _URL_RE.sub("", text)
    # Phone numbers have 9+ digits; date ranges like "2025 - 05" do not.
    return _PHONE_RE.sub(
        lambda m: "" if sum(ch.isdigit() for ch in m.group()) >= 9 else m.group(),
        text,
    )


def _heading(line: str) -> str:
    return line.strip().rstrip(":").strip().lower()


def _section(text: str, names: tuple[str, ...]) -> str:
    """Collect the lines under any of ``names`` until the next known heading.

    Headings may stand alone on a line ("EDUCATION") or end with a colon
    ("Education: BSc ..."); content on the heading line itself is kept.
    """
    wanted = set(names)
    collected: list[str] = []
    active = False
    for line in text.splitlines():
        head, sep, rest = line.partition(":")
        key = _heading(line) if _heading(line) in _ALL_HEADINGS else (_heading(head) if sep else "")
        if key in _ALL_HEADINGS:
            active = key in wanted
            if active and sep and rest.strip():
                collected.append(rest)
            continue
        if active:
            collected.append(line)
    return _clean(" ".join(collected))


def parse_cv(filename: str, data: bytes) -> dict[str, Any]:
    """Return normalized CV fields without inventing unavailable values."""
    if not data:
        raise ValueError("The uploaded CV is empty")
    try:
        text = _extract_text(filename, data)
    except (ValueError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise ValueError("The CV could not be read. Upload a valid PDF or DOCX file.") from error
    text = _redact(text)
    if not text.strip():
        raise ValueError("No readable text was found in the uploaded CV")

    lower_text = text.lower()
    skills = [
        skill.strip()
        for skill in _SKILLS
        if re.search(
            rf"(?<!\w){re.escape(skill.strip().lower())}(?!\w)",
            lower_text,
        )
    ]
    return {
        "text": _clean(text),
        "qualifications": _section(text, _SECTION_NAMES["qualifications"]),
        "certifications": _section(text, _SECTION_NAMES["certifications"]),
        "education": _section(text, _SECTION_NAMES["education"]),
        "skills": skills,
        "projects": _section(text, _SECTION_NAMES["projects"]),
        "work_experience": _section(text, _SECTION_NAMES["work_experience"]),
    }
