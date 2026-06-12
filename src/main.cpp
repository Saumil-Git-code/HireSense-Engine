#include <iostream>
#include "analyzer.h"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <vector>
#include "graph.h"
#include <algorithm>
using namespace std;
namespace fs = std::filesystem;

string to_lower(string s) {
    transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

int main(int argc, char* argv[]) {

    Analyzer analyzer;
    fs::path dataDir = (argc > 1) ? fs::path(argv[1]) : fs::path("data");

    for (const auto &entry : fs::directory_iterator(dataDir)) {
        string path = entry.path().string();
        string filename = entry.path().filename().string();

        if (path.find(".txt") != string::npos && filename != "job.txt" && filename != "output.txt") {

            ifstream file(path);
            string line;
            Resume r;
            r.filename = filename;  // Set filename

            while(getline(file, line)) {

                if(line.find("Name:") != string::npos) {
                    r.name = line.substr(6);
                }

                else if(line.find("Skills:") != string::npos) {
                    string skillsLine = line.substr(8);

                    stringstream ss(skillsLine);
                    string skill;
                    while(getline(ss, skill, ',')) {
                        if(skill[0] == ' ') skill = skill.substr(1);
                        skill = to_lower(skill);
                        r.skills.push_back(skill);
                    }
                }

                else if(line.find("Experience:") != string::npos) {
                    try {
                        r.experience = stoi(line.substr(11));
                    } catch (const std::exception&) {
                        r.experience = 0;  // Default to 0 on invalid
                    }
                }

                else if(line.find("Education:") != string::npos) {
                    r.education = line.substr(10);
                }
            }

            file.close();

            // Only add if name is present
            if (!r.name.empty()) {
                analyzer.resumes.push_back(r);
            }
        }
        
    }

string input;
ifstream jobFile((dataDir / "job.txt").string());
if (!jobFile.is_open()) {
    cerr << "Error: could not open job.txt\n";
    return 1;
}
getline(jobFile, input);
jobFile.close();

stringstream ss(input);
string skill;


while(getline(ss, skill, ',')) {
    if(skill[0] == ' ') skill = skill.substr(1);
    skill = to_lower(skill);
    analyzer.jobSkills.insert(skill);
}
Graph g;

// Load edges from skills.txt
ifstream skillsFile("../nlp/skills.txt");
if (skillsFile.is_open()) {
    string line;
    while (getline(skillsFile, line)) {
        if (line.empty()) continue;
        size_t dashPos = line.find('-');
        size_t colonPos = line.find(':');
        if (dashPos != string::npos && colonPos != string::npos && colonPos > dashPos) {
            string u = to_lower(line.substr(0, dashPos));
            string v = to_lower(line.substr(dashPos + 1, colonPos - dashPos - 1));
            int w = stoi(line.substr(colonPos + 1));
            g.addEdge(u, v, w);
        }
    }
    skillsFile.close();
} else {
    // Fallback to hardcoded if file not found
    g.addEdge("python", "ml", 1);
    g.addEdge("ml", "ai", 1);
    g.addEdge("cpp", "dsa", 1);
    g.addEdge("java", "oop", 1);
    g.addEdge("python", "data analysis", 2);
    g.addEdge("java", "spring", 2);
    g.addEdge("cpp", "embedded", 2);
    g.addEdge("ml", "data analysis", 1);
    g.addEdge("ai", "data analysis", 1);
    g.addEdge("oop", "spring", 1);
    g.addEdge("dsa", "embedded", 1);
}

analyzer.skillGraph = g;
    analyzer.analyze(dataDir.string());

    return 0;
}