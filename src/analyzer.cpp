#include<iostream>
#include "analyzer.h"
#include <queue>
#include<istream>
#include<ostream>
#include<fstream>
#include<climits>
using namespace std;

int Analyzer::longestCommonSubsequence(vector<string> seq1, vector<string> seq2) {
    int m = seq1.size();
    int n = seq2.size();
    vector<vector<int>> dp(m + 1, vector<int>(n + 1, 0));

    for (int i = 1; i <= m; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (seq1[i - 1] == seq2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }
    return dp[m][n];
}

int Analyzer::calculateScore(Resume &r) {
    int score = 0;

    for(int i = 0; i < r.skills.size(); i++) {
        if(jobSkills.find(r.skills[i]) != jobSkills.end()) {
            score += 10;
        }
    }
for(int i = 0; i < r.projects.size(); i++) {
    string project = r.projects[i];
    for(auto skill : jobSkills) {
        if(project.find(skill) != string::npos) {
            score += 5;   // less than direct skill match
        }
    }
}
for(auto jobSkill : jobSkills) {

    for(auto skill : r.skills) {
        int dist = skillGraph.shortestDistance(skill, jobSkill);
        if(dist != INT_MAX && dist <= 2) {
            score += (10 - dist * 3);  // closer = higher score
        }
    }
}
// experience-based scoring
score += r.experience * 2;  

// LCS-based scoring for skill sequence matching
vector<string> jobSkillsVec(jobSkills.begin(), jobSkills.end());
int lcs = longestCommonSubsequence(r.skills, jobSkillsVec);
score += lcs * 5;  

return score;
}
void Analyzer::analyze(const string &outputDir) {
    priority_queue<pair<int, string>> pq;

    for(int i = 0; i < resumes.size(); i++) {

        int score = calculateScore(resumes[i]);

        string identifier = resumes[i].name + " (" + resumes[i].filename + ")";
        pq.push({score, identifier});
    }

    ofstream out((outputDir + "/output.txt").c_str());
    if (!out.is_open()) {
        cerr << "Error: could not open output.txt\n";
        return;
    }

    out << "Ranking of Candidates:\n";

    while(!pq.empty()) {
        auto top = pq.top();
        pq.pop();

        out << top.second << " Score: " << top.first << "\n";
    }

    out.close();
}