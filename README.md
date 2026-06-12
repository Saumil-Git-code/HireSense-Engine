# Resume Ranking System

A sophisticated resume analysis and ranking system that automatically evaluates and ranks candidate resumes based on job requirements using graph algorithms and dynamic programming techniques.

## Features

- **Resume Upload**: Support for multiple resume formats (PDF, DOCX, TXT)
- **Job Requirement Input**: Enter required skills and qualifications
- **Intelligent Ranking**: Uses advanced algorithms to score and rank candidates
- **Web Interface**: User-friendly Flask web application
- **Skill Extraction**: Automatic skill extraction from resumes using NLP
- **Graph-Based Analysis**: Leverages skill relationship graphs for intelligent matching
- **Scoring Algorithm**: Dynamic Programming (Longest Common Subsequence) for skill matching

## Project Structure

```
DAA project/
├── src/
│   ├── main.cpp           # Entry point for C++ analyzer
│   ├── analyzer.cpp       # Resume analysis and scoring logic
│   ├── graph.cpp          # Graph implementation for skill relationships
│   └── resume.cpp         # Resume data structure
├── include/
│   ├── analyzer.h         # Analyzer class interface
│   ├── graph.h            # Graph class interface
│   └── resume.h           # Resume data structure
├── nlp/
│   ├── parser.py          # Resume text extraction from multiple formats
│   └── skills.txt         # Database of recognized skills
├── web/
│   ├── app.py             # Flask web application
│   ├── static/
│   │   └── styles.css     # Styling for web interface
│   └── templates/
│       └── index.html     # Web UI template
├── data/                  # Sample resumes and output
└── build/                 # Compiled binaries
```

## Installation

### Prerequisites
- **C++ Compiler**: GCC with C++17 support
- **Python**: 3.7 or higher
- **Windows/Linux/macOS**: Cross-platform compatible

### Step 1: Build C++ Backend

```powershell
cd "path/to/DAA project"
g++ -std=c++17 src/main.cpp src/analyzer.cpp src/graph.cpp -Iinclude -o build/app.exe
```

### Step 2: Install Python Dependencies

```powershell
pip install flask pdfplumber python-docx
```

### Step 3: Run the Web Application

```powershell
python web/app.py
```

The application will start on `http://localhost:5000`

## Usage

### Web Interface

1. **Open Browser**: Navigate to `http://localhost:5000`
2. **Enter Job Skills**: Input the required skills/qualifications in the text field
3. **Upload Resumes**: Select one or more resume files (PDF, DOCX, or TXT)
4. **Submit**: Click submit to analyze and rank the resumes
5. **View Results**: See ranked candidates with scores and details

### Sample Resume Format

Resumes should contain the following fields:
```
Name: John Doe
Skills: Python, Java, C++, SQL, Git
Experience: 5
Education: Bachelor of Science in Computer Science
```

## Algorithm Details

### Core Components

#### 1. **Resume Parser** (`nlp/parser.py`)
- Extracts text from PDF, DOCX, and TXT formats
- Identifies and extracts key fields (name, skills, experience, education)
- Normalizes skill names using the skills database

#### 2. **Skill Graph** (`include/graph.h`, `src/graph.cpp`)
- Models relationships between skills
- Uses weighted edges to represent skill similarity/connections
- Implements shortest path algorithm for skill distance calculation

#### 3. **Analyzer** (`include/analyzer.h`, `src/analyzer.cpp`)
- **Longest Common Subsequence (LCS)**: Dynamic programming approach to find skill overlap
- **Scoring Algorithm**: Combines multiple factors:
  - Skill match percentage
  - Graph distance between skills
  - Experience relevance
  - Education level

### Time Complexity
- **LCS Algorithm**: O(m × n) where m and n are skill list lengths
- **Graph Shortest Path**: O(V + E) using BFS
- **Overall Analysis**: O(n × m) for n resumes and m job skills

## Technical Stack

| Component | Technology |
|-----------|-----------|
| Backend Processing | C++ 17 |
| Resume Parsing | Python (pdfplumber, python-docx) |
| Web Framework | Flask |
| Frontend | HTML/CSS |
| Algorithms | Dynamic Programming, Graph Theory |

## File Descriptions

### C++ Backend Files

- **main.cpp**: Reads resumes from data directory, initializes analyzer
- **analyzer.cpp**: Implements scoring logic and LCS algorithm
- **graph.cpp**: Graph data structure for skill relationships
- **resume.cpp**: Resume data model with fields (name, skills, experience, education)

### Python Files

- **app.py**: Flask routes and request handling
  - GET `/`: Display home page
  - POST `/`: Process resume uploads and job requirements
  
- **parser.py**: Multi-format resume text extraction
  - Supports PDF, DOCX, TXT formats
  - Extracts structured resume data
  - Loads and applies skill normalization

### Frontend Files

- **index.html**: Web interface for job requirements and resume uploads
- **styles.css**: UI styling and layout

## Configuration

### Skills Database
Edit `nlp/skills.txt` to add or modify recognized skills. Format:
```
skill_name:category:synonyms
```

### Data Directory
- **Location**: `data/` folder
- **Contents**: Sample resumes and analyzer output
- **Output**: `output.txt` with ranking results

## Output Format

The analyzer generates `output.txt` with rankings:
```
Ranking of Candidates:
John Doe (resume.txt) Score: 95
Jane Smith (resume2.txt) Score: 87
Bob Johnson (resume3.txt) Score: 72
```

## Example Workflow

1. Upload 3 candidate resumes
2. Enter job requirements: "Python, C++, SQL, 5+ years experience"
3. System extracts skills from each resume
4. Applies LCS algorithm to match job skills with resume skills
5. Uses skill graph to evaluate related competencies
6. Generates ranked list with scores

## Performance Considerations

- **Large Resume Sets**: Efficiently processes 50+ resumes
- **Complex Skill Lists**: Handles 100+ unique skills
- **Graph Scaling**: O(V + E) complexity for skill relationship lookups

## Troubleshooting

### Build Fails
- Ensure GCC supports C++17: `g++ --version`
- Check include paths: Verify `include/` directory exists

### Python Dependencies Missing
```powershell
pip install --upgrade pip
pip install flask pdfplumber python-docx
```

### Port Already in Use
Change Flask port in `web/app.py`:
```python
if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Change port number
```

## Future Enhancements

- [ ] Database integration for resume storage
- [ ] Machine learning for skill relevance weighting
- [ ] Resume parsing improvement with AI/NLP
- [ ] Advanced filtering and search capabilities
- [ ] Export results to CSV/PDF
- [ ] User authentication and resume history

## License

Open source project for educational purposes.

## Contact & Support

For issues or questions, please check the project structure and configuration files.

---

**Last Updated**: June 2026
