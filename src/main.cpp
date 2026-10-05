#include "analyzer.h"
#include "graph.h"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <stdexcept>

namespace fs = std::filesystem;

namespace {

std::string strip_utf8_bom(const std::string& value) {
    if (value.size() >= 3 && static_cast<unsigned char>(value[0]) == 0xEF &&
        static_cast<unsigned char>(value[1]) == 0xBB &&
        static_cast<unsigned char>(value[2]) == 0xBF) {
        return value.substr(3);
    }
    return value;
}

std::string to_lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return "";
    }

    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

void parse_list(const std::string& line, Analyzer& analyzer) {
    std::stringstream ss(line);
    std::string skill;

    while (std::getline(ss, skill, ',')) {
        skill = to_lower(trim(skill));
        if (skill.empty()) {
            continue;
        }

        if (analyzer.jobSkills.insert(skill).second) {
            analyzer.jobSkillList.push_back(skill);
        }
    }
}

bool is_resume_output(const fs::directory_entry& entry) {
    return entry.is_regular_file() && entry.path().extension() == ".txt";
}

void parse_resume_file(const fs::path& path, Analyzer& analyzer) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Could not open parsed resume: " + path.string());
    }

    Resume resume;
    resume.filename = path.filename().string();

    std::string line;
    enum class Section { None, Semantic, Graph };
    Section section = Section::None;

    while (std::getline(file, line)) {
        line = strip_utf8_bom(line);
        if (line.rfind("SemanticMatches:", 0) == 0) {
            section = Section::Semantic;
            continue;
        }

        if (line.rfind("GraphMatches:", 0) == 0) {
            section = Section::Graph;
            continue;
        }

        if (section == Section::Semantic) {
            const std::string trimmed = trim(line);
            if (!trimmed.empty()) {
                resume.semanticMatches.push_back(trimmed);
                const auto arrow = trimmed.find(" -> ");
                if (arrow != std::string::npos) {
                    resume.semanticMatchedJobSkills.push_back(
                        to_lower(trim(trimmed.substr(0, arrow)))
                    );
                    const auto paren = trimmed.find(" (", arrow + 4);
                    if (paren != std::string::npos) {
                        resume.semanticMatchedCandidateSkills.push_back(
                            to_lower(trim(trimmed.substr(arrow + 4, paren - (arrow + 4))))
                        );
                    }
                }
            }
            continue;
        }

        if (section == Section::Graph) {
            if (!trim(line).empty()) {
                resume.graphMatches.push_back(trim(line));
            }
            continue;
        }

        if (line.rfind("Name:", 0) == 0) {
            resume.name = trim(line.substr(5));
        } else if (line.rfind("Skills:", 0) == 0) {
            std::stringstream ss(line.substr(7));
            std::string skill;

            while (std::getline(ss, skill, ',')) {
                skill = to_lower(trim(skill));
                if (!skill.empty()) {
                    resume.skills.push_back(skill);
                }
            }
        } else if (line.rfind("Experience:", 0) == 0) {
            try {
                resume.experience = std::stod(trim(line.substr(11)));
            } catch (...) {
                throw std::runtime_error("Invalid Experience field in " + path.string());
            }
        } else if (line.rfind("Education:", 0) == 0) {
            resume.education = trim(line.substr(10));
        } else if (line.rfind("SemanticScore:", 0) == 0) {
            try {
                resume.semanticScore = std::stod(trim(line.substr(14)));
            } catch (...) {
                throw std::runtime_error("Invalid SemanticScore field in " + path.string());
            }
        }
    }

    if (resume.name.empty() || resume.name == "Unknown") {
        throw std::runtime_error("Resume has no usable Name field: " + path.string());
    }

    analyzer.resumes.push_back(std::move(resume));
}

} // namespace

int main(int argc, char* argv[]) {
    try {
        Analyzer analyzer;
        const fs::path dataDir = (argc > 1) ? fs::path(argv[1]) : fs::path("data");

        if (!fs::is_directory(dataDir)) {
            std::cerr << "Error: data directory does not exist: " << dataDir << "\n";
            return 1;
        }

        for (const auto& entry : fs::directory_iterator(dataDir)) {
            if (!is_resume_output(entry)) {
                continue;
            }

            const std::string filename = entry.path().filename().string();
            if (filename == "job.txt" || filename == "job_profile.txt" ||
                filename == "output.txt" || filename == "results.tsv") {
                continue;
            }

            parse_resume_file(entry.path(), analyzer);
        }

        if (analyzer.resumes.empty()) {
            std::cerr << "Error: no parsed resumes found.\n";
            return 1;
        }

        std::ifstream jobProfile(dataDir / "job_profile.txt");
        if (!jobProfile.is_open()) {
            std::cerr << "Error: job_profile.txt not found. Run the parser first.\n";
            return 1;
        }

        std::string line;
        while (std::getline(jobProfile, line)) {
            line = strip_utf8_bom(line);
            if (line.rfind("Skills:", 0) == 0) {
                parse_list(line.substr(7), analyzer);
            } else if (line.rfind("MinimumExperience:", 0) == 0) {
                try {
                    analyzer.minimumExperience = std::stod(trim(line.substr(18)));
                    if (analyzer.minimumExperience < 0.0) {
                        throw std::runtime_error("Minimum experience cannot be negative.");
                    }
                } catch (...) {
                    std::cerr << "Error: invalid MinimumExperience in job_profile.txt\n";
                    return 1;
                }
            }
        }

        if (analyzer.jobSkillList.empty()) {
            std::cerr << "Error: no job skills found.\n";
            return 1;
        }

        fs::path skillsPath;
        const std::vector<fs::path> searchRoots = {
            fs::absolute(dataDir).lexically_normal(),
            fs::absolute(fs::current_path()).lexically_normal(),
            fs::absolute(fs::path(argv[0]).parent_path()).lexically_normal()
        };

        for (const fs::path& searchRoot : searchRoots) {
            fs::path searchDir = searchRoot;
            while (!searchDir.empty()) {
                const fs::path candidate = searchDir / "nlp" / "skills.txt";
                if (fs::is_regular_file(candidate)) {
                    skillsPath = candidate;
                    break;
                }

                const fs::path parent = searchDir.parent_path();
                if (parent == searchDir) {
                    break;
                }
                searchDir = parent;
            }
            if (!skillsPath.empty()) {
                break;
            }
        }

        if (skillsPath.empty()) {
            std::cerr << "Error: could not find nlp/skills.txt above data or project roots.\n";
            return 1;
        }

        Graph graph;
        std::ifstream skillsFile(skillsPath);
        if (!skillsFile.is_open()) {
            std::cerr << "Error: could not open " << skillsPath << "\n";
            return 1;
        }

        while (std::getline(skillsFile, line)) {
            line = trim(line);
            if (line.empty() || line.front() == '#') {
                continue;
            }

            const size_t colonPos = line.rfind(':');
            const size_t separatorPos = line.rfind('|', colonPos);
            if (colonPos == std::string::npos || separatorPos == std::string::npos) {
                continue;
            }

            const std::string u = to_lower(trim(line.substr(0, separatorPos)));
            const std::string v = to_lower(trim(
                line.substr(separatorPos + 1, colonPos - separatorPos - 1)
            ));

            try {
                const int weight = std::stoi(trim(line.substr(colonPos + 1)));
                graph.addEdge(u, v, weight);
            } catch (...) {
                std::cerr << "Warning: ignoring malformed graph entry: " << line << "\n";
            }
        }

        analyzer.skillGraph = std::move(graph);
        analyzer.analyze(dataDir.string());

        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "Error: " << exc.what() << "\n";
        return 1;
    }
}
