#!/usr/bin/env bash
set -euo pipefail
mkdir -p build
g++ -std=c++17 -Wall -Wextra -pedantic \
    src/main.cpp src/analyzer.cpp src/graph.cpp \
    -Iinclude -o build/app
printf 'Built build/app\n'
