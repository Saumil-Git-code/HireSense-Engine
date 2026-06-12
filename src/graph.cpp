#include<iostream>
#include "graph.h"
#include <queue>
#include<climits>
using namespace std;

void Graph::addEdge(string u, string v, int weight) {
    adj[u].push_back({v, weight});
    adj[v].push_back({u, weight});
}

int Graph::shortestDistance(string start, string target) {

    unordered_map<string, int> dist;

    for(auto &node : adj) {
        dist[node.first] = INT_MAX;
    }

    priority_queue<pair<int, string>, vector<pair<int, string>>, greater<pair<int, string>>> pq;

    dist[start] = 0;
    pq.push({0, start});

    while(!pq.empty()) {
        auto current = pq.top();
        pq.pop();

        int currDist = current.first;
        string node = current.second;

        if(node == target) return currDist;

        for(auto &neighbor : adj[node]) {
            string next = neighbor.first;
            int weight = neighbor.second;

            if(currDist + weight < dist[next]) {
                dist[next] = currDist + weight;
                pq.push({dist[next], next});
            }
        }
    }

    return INT_MAX;  // no path
}