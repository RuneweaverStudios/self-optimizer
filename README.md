# self-optimizer

**OpenClaw skill: automated self-improvement analysis and optimization proposals.**

Analyzes OpenClaw logs, chat history, and the local installation directory to detect issues and propose improvements.

## Features

- **Log Analysis**: Scans gateway and openclaw logs for errors, restarts, API key issues, and node unavailability
- **Chat History Analysis**: Identifies recurring user complaints, confusion, performance concerns, and delegation failures
- **Root Folder Scan**: Checks config validity, skill metadata, MEMORY.md size, and log directory growth
- **Improvement Proposals**: Generates actionable suggestions based on all findings

## Install

```bash
clawhub install self-optimizer
# or:
git clone https://github.com/RuneweaverStudios/self-optimizer.git
cp -r self-optimizer ~/.openclaw/workspace/skills/
```

## Quick start

```bash
# Run analysis with human-readable output
python3 scripts/self_optimizer.py analyze

# Run analysis with JSON output
python3 scripts/self_optimizer.py analyze --json

# Include chat history analysis
python3 scripts/self_optimizer.py analyze --chat-history-file /path/to/chat_history.json
```

## Requirements

- Python 3.7+
- No external dependencies (stdlib only)

## License

MIT
