#ifndef GRAPH_H
#define GRAPH_H

#include <unordered_map>
#include <vector>
#include <string>

using namespace std;

class Graph {
public:
    unordered_map<string, vector<pair<string, int>>> adj;

    void addEdge(string u, string v, int weight);
    int shortestDistance(string start, string target);
};

#endif