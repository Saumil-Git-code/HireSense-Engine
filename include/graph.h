#ifndef GRAPH_H
#define GRAPH_H

#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

class Graph {
public:
    std::unordered_map<std::string, std::vector<std::pair<std::string, int>>> adj;

    void addEdge(const std::string& u, const std::string& v, int weight);
    int shortestDistance(const std::string& start, const std::string& target) const;
};

#endif
