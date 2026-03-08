# Self Optimizer
Analyzes OpenClaw logs, chat history, and the .openclaw local root installation folder to propose self-improvement and optimization suggestions.

## Commands

- `self_optimizer.py analyze [--json]` - Runs the analysis and suggests improvements.

## Features

- **Log Analysis**: Scans `gateway.log` and `openclaw.log` for errors, restarts, and performance metrics.
- **Chat History Analysis**: Identifies recurring issues, common requests, or areas of confusion from chat transcripts. Pass a JSON file via `--chat-history-file`.
- **Root Folder Scan**: Examines `openclaw.json`, skill configurations, `MEMORY.md`, and log directory size for optimization opportunities.
- **Recommendations**: Provides actionable suggestions for performance, stability, and new skill development.
