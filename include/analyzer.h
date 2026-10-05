#ifndef ANALYZER_H
#define ANALYZER_H

#include <string>
#include <unordered_set>
#include <vector>

#include "graph.h"
#include "resume.h"

class Analyzer {
public:
    static constexpr double MAX_SKILL_POINTS = 85.0;
    static constexpr double MAX_EXPERIENCE_POINTS = 15.0;

    std::vector<Resume> resumes;
    std::vector<std::string> jobSkillList;
    std::unordered_set<std::string> jobSkills;
    Graph skillGraph;
    double minimumExperience = 0.0;

    int calculateScore(Resume& resume);
    void analyze(const std::string& outputDir);
};

#endif
