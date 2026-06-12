#ifndef RESUME_H
#define RESUME_H

#include <string>
#include <vector>
using namespace std;

struct Resume {
    string name;
    vector<string> skills;
    int experience;
    string education;
    vector<string> projects;
    string filename;  // Add filename for uniqueness
};

#endif
