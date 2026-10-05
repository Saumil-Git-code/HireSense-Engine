#ifndef RESUME_H
#define RESUME_H

#include <string>
#include <vector>

struct Resume {
    std::string name;
    std::vector<std::string> skills;
    double experience = 0.0;
    std::string education;
    double semanticScore = 0.0;

    int exactPoints = 0;
    int semanticPoints = 0;
    int graphPoints = 0;
    int experiencePoints = 0;
    int finalScore = 0;

    std::vector<std::string> exactMatches;
    std::vector<std::string> semanticMatchedJobSkills;
    std::vector<std::string> semanticMatchedCandidateSkills;
    std::vector<std::string> semanticMatches;
    std::vector<std::string> graphMatches;
    std::string filename;
};

#endif
