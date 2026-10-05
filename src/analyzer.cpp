#include "analyzer.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <limits>
#include <stdexcept>
#include <unordered_set>

int Analyzer::calculateScore(Resume& resume) {
    resume.exactMatches.clear();
    resume.exactPoints = 0;
    resume.semanticPoints = 0;
    resume.graphPoints = 0;
    resume.experiencePoints = 0;
    resume.graphMatches.clear();

    if (jobSkillList.empty()) {
        resume.finalScore = 0;
        return 0;
    }

    const std::unordered_set<std::string> candidateSkills(
        resume.skills.begin(), resume.skills.end()
    );

    // Track candidate skills committed to exact or semantic tiers
    // to strictly enforce 1-to-1 evidence assignment across all tiers.
    std::unordered_set<std::string> consumedCandidateSkills;

    for (const std::string& jobSkill : jobSkillList) {
        if (candidateSkills.find(jobSkill) != candidateSkills.end()) {
            resume.exactMatches.push_back(jobSkill);
            consumedCandidateSkills.insert(jobSkill);
        }
    }

    const double exactCoverage = static_cast<double>(resume.exactMatches.size()) /
                                 static_cast<double>(jobSkillList.size());
    resume.exactPoints = static_cast<int>(std::lround(exactCoverage * MAX_SKILL_POINTS));

    // Semantic score is normalized over all job skills and excludes exact matches.
    resume.semanticPoints = static_cast<int>(std::lround(
        std::clamp(resume.semanticScore, 0.0, 1.0) * MAX_SKILL_POINTS
    ));
    resume.semanticPoints = std::min(
        resume.semanticPoints,
        std::max(0, static_cast<int>(MAX_SKILL_POINTS) - resume.exactPoints)
    );

    // Add candidate skills matched in semantic tier to consumed set
    for (const std::string& candSkill : resume.semanticMatchedCandidateSkills) {
        consumedCandidateSkills.insert(candSkill);
    }

    const std::unordered_set<std::string> exactJobSkills(
        resume.exactMatches.begin(), resume.exactMatches.end()
    );
    const std::unordered_set<std::string> semanticJobSkills(
        resume.semanticMatchedJobSkills.begin(),
        resume.semanticMatchedJobSkills.end()
    );

    double graphCredit = 0.0;
    for (const std::string& jobSkill : jobSkillList) {
        if (exactJobSkills.count(jobSkill) || semanticJobSkills.count(jobSkill)) {
            continue;
        }

        int bestDistance = std::numeric_limits<int>::max();
        std::string bestCandidateSkill;

        // Bipartite matching: Only consider candidate skills NOT yet consumed
        for (const std::string& candidateSkill : resume.skills) {
            if (consumedCandidateSkills.count(candidateSkill)) {
                continue;
            }

            const int distance = skillGraph.shortestDistance(candidateSkill, jobSkill);
            if (distance < bestDistance) {
                bestDistance = distance;
                bestCandidateSkill = candidateSkill;
            }
        }

        if (bestDistance == 1 && !bestCandidateSkill.empty()) {
            graphCredit += 1.0;
            consumedCandidateSkills.insert(bestCandidateSkill); // 1-to-1 matching: consume this candidate skill
            resume.graphMatches.push_back(
                jobSkill + " <- " + bestCandidateSkill + " (distance 1)"
            );
        } else if (bestDistance == 2 && !bestCandidateSkill.empty()) {
            graphCredit += 0.5;
            consumedCandidateSkills.insert(bestCandidateSkill); // 1-to-1 matching: consume this candidate skill
            resume.graphMatches.push_back(
                jobSkill + " <- " + bestCandidateSkill + " (distance 2)"
            );
        }
    }

    graphCredit /= static_cast<double>(jobSkillList.size());
    resume.graphPoints = static_cast<int>(std::lround(graphCredit * MAX_SKILL_POINTS));
    resume.graphPoints = std::min(
        resume.graphPoints,
        std::max(0, static_cast<int>(MAX_SKILL_POINTS) - resume.exactPoints - resume.semanticPoints)
    );

    int skillScore = std::min(
        static_cast<int>(MAX_SKILL_POINTS),
        resume.exactPoints + resume.semanticPoints + resume.graphPoints
    );

    if (minimumExperience > 0.0) {
        const double experienceRatio = std::min(
            1.0,
            resume.experience / minimumExperience
        );
        resume.experiencePoints = static_cast<int>(
            std::lround(experienceRatio * MAX_EXPERIENCE_POINTS)
        );
        resume.finalScore = std::min(100, skillScore + resume.experiencePoints);
    } else {
        // Without experience, scale subcomponents proportionally to /100 so they sum to finalScore
        const double scale = 100.0 / MAX_SKILL_POINTS;
        resume.exactPoints = static_cast<int>(std::lround(resume.exactPoints * scale));
        resume.semanticPoints = static_cast<int>(std::lround(resume.semanticPoints * scale));
        resume.graphPoints = static_cast<int>(std::lround(resume.graphPoints * scale));
        resume.finalScore = std::min(100, resume.exactPoints + resume.semanticPoints + resume.graphPoints);
    }

    return resume.finalScore;
}

void Analyzer::analyze(const std::string& outputDir) {
    for (Resume& resume : resumes) {
        calculateScore(resume);
    }

    std::vector<int> order(resumes.size());
    for (size_t i = 0; i < resumes.size(); ++i) {
        order[i] = static_cast<int>(i);
    }

    std::sort(order.begin(), order.end(), [this](int a, int b) {
        if (resumes[a].finalScore != resumes[b].finalScore) {
            return resumes[a].finalScore > resumes[b].finalScore;
        }
        if (resumes[a].semanticPoints != resumes[b].semanticPoints) {
            return resumes[a].semanticPoints > resumes[b].semanticPoints;
        }
        return resumes[a].name < resumes[b].name;
    });

    std::ofstream output(outputDir + "/output.txt");
    std::ofstream results(outputDir + "/results.tsv");

    if (!output.is_open() || !results.is_open()) {
        throw std::runtime_error("Could not create analyzer output files.");
    }

    output << "HireSense Candidate Ranking\n";
    output << "===========================\n\n";
    output << "Required skills: ";
    for (size_t i = 0; i < jobSkillList.size(); ++i) {
        if (i > 0) output << ", ";
        output << jobSkillList[i];
    }
    output << "\n";

    if (minimumExperience > 0.0) {
        output << "Minimum experience: " << minimumExperience << " years\n";
    } else {
        output << "Minimum experience: not requested\n";
    }

    output << "\nScoring: skill evidence 85 points + experience 15 points when requested\n";
    output << "\n";

    results << "Rank\tName\tFilename\tScore\tExactPoints\tSemanticPoints\tGraphPoints\tExperiencePoints\tExactMatches\tSemanticMatches\tGraphMatches\n";

    for (size_t rank = 0; rank < order.size(); ++rank) {
        Resume& resume = resumes[order[rank]];
        const int displayRank = static_cast<int>(rank) + 1;

        output << "#" << displayRank << " " << resume.name << "\n";
        output << "Score: " << resume.finalScore << "/100\n";
        output << "Exact evidence: " << resume.exactPoints << " points\n";
        output << "Semantic evidence: " << resume.semanticPoints << " points\n";
        output << "Graph evidence: " << resume.graphPoints << " points\n";

        if (minimumExperience > 0.0) {
            output << "Experience: " << resume.experiencePoints << "/15\n";
        } else {
            output << "Experience: not requested\n";
        }

        output << "Exact evidence: ";
        for (size_t i = 0; i < resume.exactMatches.size(); ++i) {
            if (i > 0) output << ", ";
            output << resume.exactMatches[i];
        }
        output << "\n";

        output << "Semantic evidence:\n";
        for (const std::string& match : resume.semanticMatches) {
            output << "  - " << match << "\n";
        }
        if (resume.semanticMatches.empty()) {
            output << "  - none\n";
        }

        output << "Graph evidence:\n";
        for (const std::string& match : resume.graphMatches) {
            output << "  - " << match << "\n";
        }
        if (resume.graphMatches.empty()) {
            output << "  - none\n";
        }

        output << "Education: " << resume.education << "\n";
        output << "----------------------------------------\n";

        results << displayRank << '\t'
                << resume.name << '\t'
                << resume.filename << '\t'
                << resume.finalScore << '\t'
                << resume.exactPoints << '\t'
                << resume.semanticPoints << '\t'
                << resume.graphPoints << '\t'
                << resume.experiencePoints << '\t';

        for (size_t i = 0; i < resume.exactMatches.size(); ++i) {
            if (i > 0) results << ',';
            results << resume.exactMatches[i];
        }

        results << '\t';
        for (size_t i = 0; i < resume.semanticMatches.size(); ++i) {
            if (i > 0) results << " || ";
            results << resume.semanticMatches[i];
        }

        results << '\t';
        for (size_t i = 0; i < resume.graphMatches.size(); ++i) {
            if (i > 0) results << " || ";
            results << resume.graphMatches[i];
        }
        results << '\n';
    }
}
