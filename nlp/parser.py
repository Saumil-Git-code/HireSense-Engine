import json
import os
import re
import sys
from typing import Dict, List, Tuple

import pdfplumber
from docx import Document

try:
    from .semantic import semantic_skill_matching
except ImportError:  # Supports running parser.py directly from nlp/
    from semantic import semantic_skill_matching

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB_PATH = os.path.join(BASE, "nlp", "skill_vocabulary.json")

SECTION_ALIASES = {
    "education": "education",
    "education & certifications": "education",
    "education and certifications": "education",
    "academic background": "education",
    "experience": "experience",
    "professional experience": "experience",
    "work experience": "experience",
    "employment": "experience",
    "technical skills": "skills",
    "technical & soft skills": "skills",
    "skills": "skills",
    "core competencies": "skills",
    "projects": "projects",
    "selected projects": "projects",
    "key projects": "projects",
    "certifications": "certifications",
    "professional summary": "summary",
    "summary": "summary",
    "profile": "summary",
    "coursework": "coursework",
    "relevant coursework": "coursework",
}
ALLOWED_SKILL_SECTIONS = {"skills", "experience", "projects", "summary", "coursework", "certifications"}
EDUCATION_SECTIONS = {"education"}
EXPERIENCE_SECTIONS = {"experience"}


def normalize_heading(line: str) -> str:
    cleaned = re.sub(r"[\s:|]+", " ", line.lower()).strip()
    return cleaned


def section_type(line: str) -> str | None:
    return SECTION_ALIASES.get(normalize_heading(line))


def load_vocabulary() -> Dict[str, List[str]]:
    with open(VOCAB_PATH, "r", encoding="utf-8") as file:
        raw = json.load(file)
    return {
        canonical.lower(): sorted(
            {canonical.lower(), *(alias.lower() for alias in aliases)},
            key=len,
            reverse=True,
        )
        for canonical, aliases in raw.items()
    }


def build_alias_lookup(vocabulary: Dict[str, List[str]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canonical, aliases in vocabulary.items():
        for alias in aliases:
            lookup[alias] = canonical
    return lookup


def read_pdf(file_path: str) -> str:
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
    return "\n".join(pages)


def read_docx(file_path: str) -> str:
    document = Document(file_path)
    return "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    )


def strip_bom(value: str) -> str:
    return value.lstrip("\ufeff")


def read_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return strip_bom(file.read())


def read_document(file_path: str) -> str:
    extension = os.path.splitext(file_path)[1].lower()
    readers = {
        ".pdf": read_pdf,
        ".docx": read_docx,
        ".txt": read_text_file,
    }
    if extension not in readers:
        raise ValueError(f"Unsupported file type: {extension}")
    return readers[extension](file_path).strip()


def extract_sections(text: str) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {key: [] for key in set(SECTION_ALIASES.values())}
    current = "header"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        detected = section_type(line)
        if detected:
            current = detected
            continue

        sections.setdefault(current, []).append(line)

    return sections


def clean_text_for_matching(lines: List[str]) -> str:
    return "\n".join(lines).lower()


def regex_for_alias(alias: str) -> str:
    # Boundary-aware matching that still supports tokens such as C++ and C#.
    return rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"


def extract_skills(
    sections: Dict[str, List[str]],
    vocabulary: Dict[str, List[str]],
    additional_skills: List[str] | None = None,
) -> List[str]:
    searchable_text = clean_text_for_matching(
        [line for section in ALLOWED_SKILL_SECTIONS for line in sections.get(section, [])]
    )

    found = set()
    for canonical, aliases in vocabulary.items():
        for alias in aliases:
            if re.search(regex_for_alias(alias), searchable_text, re.IGNORECASE):
                found.add(canonical)
                break

    # Allow user-supplied job requirements that are not yet in the vocabulary
    # to be detected literally. These terms do not participate in graph scoring.
    for skill in additional_skills or []:
        normalized_skill = skill.strip().lower()
        if normalized_skill and re.search(
            regex_for_alias(normalized_skill), searchable_text, re.IGNORECASE
        ):
            found.add(normalized_skill)

    return sorted(found)


def extract_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines[:15]:
        if line.lower().startswith("name:"):
            value = line.split(":", 1)[1].strip()
            if value:
                return value.title()

    excluded = ("phone", "email", "address", "linkedin", "github", "resume", "curriculum")
    for line in lines[:8]:
        if "@" in line or len(line.split()) > 4:
            continue
        if not any(word in line.lower() for word in excluded):
            return line.title()

    return "Unknown"


def extract_experience(sections: Dict[str, List[str]]) -> float:
    # Check both experience and summary sections
    combined_lines = sections.get("experience", []) + sections.get("summary", [])
    text = clean_text_for_matching(combined_lines)

    # 1. Check for explicit total experience statements: "X years of experience"
    totals = re.findall(
        r"(?:over|more than|approximately|about|total of)?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?\s*(?:of)?\s*(?:professional|industry|work)?\s*experience",
        text,
    )
    if totals:
        return max(float(v) for v in totals)

    # 2. Extract year ranges e.g., 2019 - 2022, 2021 - Present
    current_year = 2026
    year_ranges = re.findall(
        r"\b(19\d\d|20\d\d)\s*(?:-|–|to)\s*(19\d\d|20\d\d|present|current)\b",
        text,
        re.IGNORECASE,
    )

    total_years = 0.0
    for start_str, end_str in year_ranges:
        start = int(start_str)
        if end_str.lower() in ("present", "current"):
            end = current_year
        else:
            end = int(end_str)
        if 1980 <= start <= current_year and start <= end <= current_year + 1:
            diff = end - start
            total_years += max(diff, 0.5)

    if total_years > 0:
        return min(round(total_years, 1), 40.0)

    # 3. Fallback to any explicit "X years"
    explicit = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", text)
    if explicit:
        return max(float(v) for v in explicit)

    return 0.0


def extract_education(sections: Dict[str, List[str]]) -> str:
    lines = sections.get("education", [])
    return " | ".join(lines[:4]) if lines else "Unknown"


def canonicalize_skill(raw_skill: str, alias_lookup: Dict[str, str]) -> str:
    normalized = re.sub(r"\s+", " ", raw_skill.lower().strip())
    return alias_lookup.get(normalized, normalized)


def parse_job_input(raw_text: str, alias_lookup: Dict[str, str]) -> Tuple[List[str], float, List[str]]:
    job_skills: List[str] = []
    minimum_experience = 0.0
    text = strip_bom(raw_text)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()
        if lower.startswith("skills:"):
            values = line.split(":", 1)[1].split(",")
            job_skills.extend(canonicalize_skill(value, alias_lookup) for value in values)
        elif lower.startswith("minimumexperience:"):
            value = line.split(":", 1)[1].strip()
            try:
                minimum_experience = float(value)
            except ValueError:
                raise ValueError("MinimumExperience must be a non-negative number.")

    if not job_skills:
        # Legacy support: a raw comma-separated skill list.
        for line in text.splitlines():
            if not line.lower().startswith("minimumexperience:"):
                job_skills.extend(
                    canonicalize_skill(value, alias_lookup)
                    for value in line.split(",")
                )

    if minimum_experience < 0:
        raise ValueError("MinimumExperience cannot be negative.")

    seen = set()
    cleaned = []
    for skill in job_skills:
        if skill and skill not in seen:
            seen.add(skill)
            cleaned.append(skill)

    unknown = [skill for skill in cleaned if skill not in alias_lookup.values()]
    return cleaned, minimum_experience, unknown


def build_candidate(
    text: str,
    vocabulary: Dict[str, List[str]],
    additional_skills: List[str] | None = None,
) -> Dict:
    sections = extract_sections(text)
    return {
        "name": extract_name(text),
        "skills": extract_skills(sections, vocabulary, additional_skills),
        "experience": extract_experience(sections),
        "education": extract_education(sections),
    }


def process_file(
    file_path: str,
    output_folder: str,
    job_skills: List[str],
    vocabulary: Dict[str, List[str]],
    alias_lookup: Dict[str, str],
) -> None:
    text = read_document(file_path)
    candidate = build_candidate(text, vocabulary, job_skills)

    exact_job_skills = set(job_skills).intersection(candidate["skills"])
    semantic_score, semantic_matches = semantic_skill_matching(
        job_skills,
        candidate["skills"],
        exact_job_skills=exact_job_skills,
    )

    source_name = os.path.basename(file_path)
    candidate["source_file"] = source_name
    candidate["semantic_score"] = semantic_score
    candidate["semantic_matches"] = semantic_matches

    base_name = os.path.splitext(source_name)[0]
    output_path = os.path.join(output_folder, f"{base_name}.txt")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(f"Name: {candidate['name']}\n")
        file.write("Skills: " + ", ".join(candidate["skills"]) + "\n")
        file.write(f"Experience: {candidate['experience']}\n")
        file.write(f"Education: {candidate['education']}\n")
        file.write(f"SourceFile: {source_name}\n")
        file.write(f"SemanticScore: {candidate['semantic_score']}\n")
        file.write("SemanticMatches:\n")
        for job_skill, candidate_skill, similarity in semantic_matches:
            file.write(f"{job_skill} -> {candidate_skill} ({similarity:.4f})\n")


def process_directory(folder: str) -> List[str]:
    job_file = os.path.join(folder, "job.txt")
    if not os.path.isfile(job_file):
        raise FileNotFoundError(f"job.txt not found in {folder}")

    vocabulary = load_vocabulary()
    alias_lookup = build_alias_lookup(vocabulary)

    with open(job_file, "r", encoding="utf-8-sig") as file:
        raw_job_text = file.read()

    job_skills, minimum_experience, unknown_skills = parse_job_input(raw_job_text, alias_lookup)

    if not job_skills:
        raise ValueError("No required skills were provided.")

    job_profile_path = os.path.join(folder, "job_profile.txt")
    with open(job_profile_path, "w", encoding="utf-8") as file:
        file.write("Skills: " + ", ".join(job_skills) + "\n")
        file.write(f"MinimumExperience: {minimum_experience}\n")
        if unknown_skills:
            file.write("UnknownSkills: " + ", ".join(unknown_skills) + "\n")

    processed = []
    ignored = {"job.txt", "job_profile.txt", "output.txt", "results.tsv"}

    for filename in sorted(os.listdir(folder)):
        if filename in ignored:
            continue
        extension = os.path.splitext(filename)[1].lower()
        if extension not in {".pdf", ".docx"}:
            continue

        file_path = os.path.join(folder, filename)
        process_file(file_path, folder, job_skills, vocabulary, alias_lookup)
        processed.append(filename)

    if not processed:
        raise ValueError("No supported resume files (.pdf or .docx) were found.")

    return unknown_skills


def main() -> int:
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data")

    try:
        unknown = process_directory(folder)
        for skill in unknown:
            print(f"Warning: '{skill}' is not in the skill vocabulary/graph; exact and semantic matching can still use it.")
        print(f"Successfully processed resumes in {folder}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
