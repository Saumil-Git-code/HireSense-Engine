import pdfplumber
import os
import sys
from docx import Document
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
def read_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text.lower()

def load_skills():
    skills = set()
    with open(os.path.join(BASE, "nlp", "skills.txt"), "r") as f:
        for line in f:
            line = line.strip()
            if line:
                # Extract skills from "u-v:w" format
                dash_pos = line.find('-')
                colon_pos = line.find(':')
                if dash_pos != -1 and colon_pos != -1:
                    u = line[:dash_pos].strip()
                    v = line[dash_pos+1:colon_pos].strip()
                    skills.add(u.lower())
                    skills.add(v.lower())
                else:
                    # Fallback for old format
                    skills.add(line.lower())
    return list(skills)

def extract_skills(text, skills_list):
    found = []
    for skill in skills_list:
        if skill in text:
            found.append(skill)
    return found
def extract_name(text):
    lines = text.split("\n")
    # First, check for explicit "Name:" lines
    for line in lines:
        line = line.strip()
        if line.lower().startswith("name:"):
            name = line[5:].strip()  # Remove "Name:"
            if name and not any(char.isdigit() for char in name):  # No numbers
                return name.title()  # Capitalize properly
    
    # Fallback: Original logic with filters
    for line in lines:
        line = line.strip()
        if len(line) > 0 and len(line.split()) <= 4 and "@" not in line:
            # Exclude common non-name lines
            exclude_words = ["phone", "email", "address", "linkedin", "github"]
            if not any(word in line.lower() for word in exclude_words):
                return line.title()
    
    return "Unknown"

def extract_experience(text):
    import re
    # Look for patterns like "2 years", "3+ years", etc.
    match = re.search(r'(\d+)\s*years?', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0  # Default if not found

def process_file(file_path, output_folder):
    skills_list = load_skills()

    text = read_pdf(file_path)
    found_skills = extract_skills(text, skills_list)

    # create output file name in the same folder as the uploaded PDFs
    base_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(base_name)[0]
    name = extract_name(text)
    experience = extract_experience(text)
    output_path = os.path.join(output_folder, f"{name_without_ext}.txt")
    with open(output_path, "w") as f:
        f.write(f"Name: {name}\n")
        f.write("Skills: " + ", ".join(found_skills) + "\n")
        f.write(f"Experience: {experience}\n")
        f.write("Education: BTech\n")

    print(f"Processed {file_path} -> {output_path}")

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data")
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            process_file(os.path.join(folder, file), folder)

if __name__ == "__main__":
    main()