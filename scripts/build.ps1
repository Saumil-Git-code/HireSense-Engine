$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "build" | Out-Null

g++ -std=c++17 -Wall -Wextra -pedantic `
    src/main.cpp src/analyzer.cpp src/graph.cpp `
    -Iinclude -o build/app.exe

Write-Host "Built build/app.exe"
