import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from csv import DictReader

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from nlp.parser import process_directory


def strip_bom(value):
    return value.lstrip("\ufeff")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB total request size.

BUILD_DIR = os.path.join(BASE, "build")
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def analyzer_executable():
    filename = "app.exe" if os.name == "nt" else "app"
    return os.path.join(BUILD_DIR, filename)


def read_resume_summary(path):
    data = {
        "name": "Unknown",
        "skills": [],
        "experience": 0.0,
        "education": "Not specified",
        "semantic_matches": [],
        "graph_matches": [],
    }

    with open(path, "r", encoding="utf-8-sig") as file:
        semantic_section = False
        for raw_line in file:
            line = strip_bom(raw_line.rstrip("\n"))

            if line == "SemanticMatches:":
                semantic_section = "semantic"
                continue

            if line == "GraphMatches:":
                semantic_section = "graph"
                continue

            if semantic_section == "semantic":
                if line.strip():
                    data["semantic_matches"].append(line.strip())
                continue

            if semantic_section == "graph":
                if line.strip():
                    data["graph_matches"].append(line.strip())
                continue

            if line.startswith("Name:"):
                data["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Skills:"):
                data["skills"] = [
                    skill.strip()
                    for skill in line.split(":", 1)[1].split(",")
                    if skill.strip()
                ]
            elif line.startswith("Experience:"):
                try:
                    data["experience"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    data["experience"] = 0.0
            elif line.startswith("Education:"):
                data["education"] = line.split(":", 1)[1].strip()

    return data


def read_job_profile(path):
    skills = []
    unknown = []

    with open(path, "r", encoding="utf-8-sig") as file:
        for raw_line in file:
            line = strip_bom(raw_line.rstrip("\n"))
            if line.startswith("Skills:"):
                skills = [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]
            elif line.startswith("UnknownSkills:"):
                unknown = [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]

    return skills, unknown


def render_error(message):
    return render_template(
        "index.html",
        rankings=[],
        error=message,
        required_skills=[],
        unknown_skills=[],
        min_experience=0,
    )


@app.errorhandler(413)
def request_too_large(_error):
    return render_error("Upload is too large. Please keep the total request under 25 MB."), 413


@app.route("/", methods=["GET", "POST"])
def home():
    rankings = []
    error = None
    required_skills = []
    unknown_skills = []
    min_experience = 0

    if request.method == "POST":
        skills = request.form.get("skills", "").strip()
        min_experience_raw = request.form.get("min_experience", "").strip()

        if not skills:
            return render_error("Please enter at least one required skill.")

        try:
            min_experience = float(min_experience_raw) if min_experience_raw else 0.0
            if min_experience < 0:
                raise ValueError
        except ValueError:
            return render_error("Minimum experience must be a non-negative number.")

        resumes = request.files.getlist("resumes")
        valid_resumes = [f for f in resumes if f and f.filename]
        if not valid_resumes:
            return render_error("Please upload at least one PDF or DOCX resume.")

        temp_dir = tempfile.mkdtemp(prefix="hiresense_")

        try:
            with open(os.path.join(temp_dir, "job.txt"), "w", encoding="utf-8-sig") as file:
                file.write(f"Skills: {skills}\n")
                file.write(f"MinimumExperience: {min_experience}\n")

            uploaded_count = 0
            for uploaded_file in valid_resumes:
                safe_name = secure_filename(uploaded_file.filename)
                extension = os.path.splitext(safe_name)[1].lower()

                if not safe_name or extension not in ALLOWED_EXTENSIONS:
                    continue

                # Prevent same-name uploads from overwriting one another.
                unique_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
                uploaded_file.save(os.path.join(temp_dir, unique_name))
                uploaded_count += 1

            if uploaded_count == 0:
                return render_error("No valid PDF/DOCX resumes were uploaded.")

            unknown_skills = process_directory(temp_dir)
            required_skills, _ = read_job_profile(os.path.join(temp_dir, "job_profile.txt"))

            executable = analyzer_executable()
            if not os.path.isfile(executable):
                return render_error(
                    f"Analyzer executable not found at '{executable}'. "
                    "Build the C++ analyzer first."
                )

            analyzer_result = subprocess.run(
                [executable, temp_dir],
                capture_output=True,
                text=True,
                cwd=BASE,
                timeout=60,
                check=False,
            )

            if analyzer_result.returncode != 0:
                details = analyzer_result.stderr.strip() or analyzer_result.stdout.strip()
                return render_error(details or "The analyzer failed without an error message.")

            results_path = os.path.join(temp_dir, "results.tsv")
            if not os.path.isfile(results_path):
                return render_error("Analyzer completed but did not produce results.tsv.")

            with open(results_path, "r", encoding="utf-8", newline="") as file:
                for row in DictReader(file, delimiter="\t"):
                    resume_path = os.path.join(temp_dir, row["Filename"])
                    resume_data = read_resume_summary(resume_path)

                    exact_matches = [
                        skill.strip()
                        for skill in row.get("ExactMatches", "").split(",")
                        if skill.strip()
                    ]

                    graph_matches = [
                        match.strip()
                        for match in row.get("GraphMatches", "").split(" || ")
                        if match.strip()
                    ]

                    rankings.append({
                        "rank": int(row["Rank"]),
                        "name": row["Name"],
                        "score": int(row["Score"]),
                        "exact_points": int(row["ExactPoints"]),
                        "semantic_points": int(row["SemanticPoints"]),
                        "graph_points": int(row["GraphPoints"]),
                        "experience_points": int(row["ExperiencePoints"]),
                        "skills": resume_data["skills"],
                        "exact_matches": exact_matches,
                        "semantic_matches": resume_data["semantic_matches"],
                        "graph_matches": graph_matches,
                        "experience": resume_data["experience"],
                        "education": resume_data["education"],
                    })

        except subprocess.TimeoutExpired:
            error = "Analysis timed out. Try fewer or smaller resumes."
        except (OSError, ValueError) as exc:
            error = str(exc)
        except Exception as exc:
            error = f"Unexpected error: {exc}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return render_template(
        "index.html",
        rankings=rankings,
        error=error,
        required_skills=required_skills,
        unknown_skills=unknown_skills,
        min_experience=min_experience,
    )


if __name__ == "__main__":
    app.run(debug=False)
