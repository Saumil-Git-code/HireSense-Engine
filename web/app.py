from flask import Flask, render_template, request
import os
import subprocess
import shutil
import tempfile

app = Flask(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE, "data")
NLP_DIR   = os.path.join(BASE, "nlp")
BUILD_DIR = os.path.join(BASE, "build")

@app.route("/", methods=["GET", "POST"])
def home():
    rankings = []  # Initialize to avoid UnboundLocalError

    if request.method == "POST":
        skills = request.form["skills"]

        # Create a temporary workspace for this upload session
        temp_dir = tempfile.mkdtemp(prefix="session_", dir=DATA_DIR)
        try:
            with open(os.path.join(temp_dir, "job.txt"), "w") as f:
                f.write(skills)

            uploaded_files = []
            for file in request.files.getlist("resumes"):
                if file.filename != "":
                    dest_path = os.path.join(temp_dir, file.filename)
                    file.save(dest_path)
                    uploaded_files.append(dest_path)

            if not uploaded_files:
                return render_template("index.html", output="No resumes uploaded.")

            # 3. Run parser on only the selected files
            result = subprocess.run(
                ["python", os.path.join(NLP_DIR, "parser.py"), temp_dir],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                return render_template("index.html", output="Parser Error:\n" + result.stderr)

            # 4. Run C++ analyzer against the selected session folder
            result = subprocess.run(
                [os.path.join(BUILD_DIR, "app.exe"), temp_dir],
                capture_output=True, text=True, cwd=BASE
            )
            if result.returncode != 0:
                return render_template("index.html", output="C++ Error:\n" + result.stderr)

            # 5. Read and parse output
            output_file = os.path.join(temp_dir, "output.txt")
            rankings = []
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # Skip "Ranking of Candidates:"
                        if "Score:" in line:
                            parts = line.strip().split(" Score: ")
                            if len(parts) == 2:
                                identifier = parts[0]
                                try:
                                    score = int(parts[1])

                                    # Extract additional data from processed resume file
                                    resume_data = {}
                                    # Parse identifier to get filename (e.g., "Jordan Smith (Junior_Software_Developer_Resume.txt)")
                                    if "(" in identifier and ")" in identifier:
                                        filename = identifier.split("(")[1].split(")")[0]
                                        resume_file = os.path.join(temp_dir, filename)
                                        if os.path.exists(resume_file):
                                            with open(resume_file, "r") as rf:
                                                for resume_line in rf:
                                                    if resume_line.startswith("Name:"):
                                                        resume_data["name"] = resume_line.split(":", 1)[1].strip()
                                                    elif resume_line.startswith("Skills:"):
                                                        skills_str = resume_line.split(":", 1)[1].strip()
                                                        resume_data["skills"] = [s.strip() for s in skills_str.split(",") if s.strip()]
                                                    elif resume_line.startswith("Experience:"):
                                                        try:
                                                            resume_data["experience"] = int(resume_line.split(":", 1)[1].strip())
                                                        except ValueError:
                                                            resume_data["experience"] = 0
                                                    elif resume_line.startswith("Education:"):
                                                        resume_data["education"] = resume_line.split(":", 1)[1].strip()

                                    candidate = {
                                        "identifier": identifier,
                                        "score": score,
                                        "name": resume_data.get("name", identifier.split(" (")[0]),
                                        "skills": resume_data.get("skills", []),
                                        "experience": resume_data.get("experience", 0),
                                        "education": resume_data.get("education", "Not specified")
                                    }
                                    rankings.append(candidate)

                                except ValueError:
                                    pass  # Skip invalid lines
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return render_template("index.html", rankings=rankings)

if __name__ == "__main__":
    app.run(debug=True)