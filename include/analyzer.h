#ifndef ANALYZER_H
#define ANALYZER_H

#include <vector>
#include <string>
#include <unordered_set>
#include "resume.h"
#include "graph.h"

using namespace std;

class Analyzer {
public:
    vector<Resume> resumes;
    unordered_set<string> jobSkills;
    Graph skillGraph;

    int calculateScore(Resume &r);
    int longestCommonSubsequence(vector<string> seq1, vector<string> seq2);
    void analyze(const string &outputDir);
};

#endif