#include "graph.h"

#include <climits>
#include <functional>
#include <queue>
#include <unordered_map>

void Graph::addEdge(const std::string& u, const std::string& v, int weight) {
    if (weight < 0) {
        return; // Dijkstra requires non-negative edge weights.
    }

    adj[u].push_back({v, weight});
    adj[v].push_back({u, weight});
}

int Graph::shortestDistance(const std::string& start, const std::string& target) const {
    if (start == target) {
        return 0;
    }

    std::unordered_map<std::string, int> dist;
    std::priority_queue<
        std::pair<int, std::string>,
        std::vector<std::pair<int, std::string>>,
        std::greater<std::pair<int, std::string>>
    > pq;

    dist[start] = 0;
    pq.push({0, start});

    while (!pq.empty()) {
        const auto [currentDistance, node] = pq.top();
        pq.pop();

        auto known = dist.find(node);
        if (known == dist.end() || currentDistance != known->second) {
            continue;
        }

        if (node == target) {
            return currentDistance;
        }

        auto nodeIt = adj.find(node);
        if (nodeIt == adj.end()) {
            continue;
        }

        for (const auto& [next, weight] : nodeIt->second) {
            const int newDistance = currentDistance + weight;
            auto nextIt = dist.find(next);

            if (nextIt == dist.end() || newDistance < nextIt->second) {
                dist[next] = newDistance;
                pq.push({newDistance, next});
            }
        }
    }

    return INT_MAX;
}
