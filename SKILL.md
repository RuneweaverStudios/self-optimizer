---
name: self-optimizer
displayName: Self Optimizer
description: Analyzes OpenClaw logs, chat history, and the local installation folder to propose self-improvement and optimization suggestions.
version: 1.0.0
---

# Self Optimizer

Analyzes OpenClaw logs, chat history, and the `.openclaw` local root installation folder to propose self-improvement and optimization suggestions.

## Installation

```bash
clawhub install self-optimizer
# or: git clone https://github.com/RuneweaverStudios/self-optimizer.git workspace/skills/self-optimizer
```

## Requirements

- Python 3.7+
- No external dependencies (uses only stdlib)

## Usage

```bash
# Run analysis with human-readable output
python3 scripts/self_optimizer.py analyze

# Run analysis with JSON output
python3 scripts/self_optimizer.py analyze --json

# Include chat history analysis
python3 scripts/self_optimizer.py analyze --chat-history-file /path/to/chat_history.json
```

## Commands

- **analyze** - Run the full analysis pipeline and generate improvement proposals.
  - `--json` - Output results in structured JSON format.
  - `--chat-history-file PATH` - Path to a JSON file containing chat history data for analysis.

## What It Analyzes

### Log Analysis
Scans `gateway.log` and `openclaw.log` (last 500 lines, last 60 minutes) for:
- Errors and exceptions
- Gateway restarts (SIGUSR1/SIGTERM patterns)
- OpenRouter 403 / key limit errors
- Node unavailability mentions
- Configuration change events

### Chat History Analysis
When provided a chat history JSON file, identifies:
- Recurring error mentions from the user
- User confusion signals
- Performance and cost concerns
- Service unavailability complaints
- Sub-agent delegation failures

### Root Folder Scan
Examines the OpenClaw home directory for:
- `openclaw.json` validity and configuration issues
- Skill count and missing `_meta.json` files
- `MEMORY.md` size (warns if too large or empty)
- Log directory size (warns if over 100 MB)
- Default model configuration

## Output Format

### Human-Readable
Prints a structured report with sections for log analysis, chat history, root folder findings, and numbered improvement proposals.

### JSON (`--json`)
```json
{
  "log_analysis": {
    "errors": ["..."],
    "restarts": 0,
    "config_changes": 0,
    "openrouter_403s": 0,
    "node_unavailable_mentions": 0,
    "suggestions": ["..."]
  },
  "chat_history_analysis": {
    "status": "Analyzed",
    "issues_summary": {"error": 2, "performance": 1},
    "suggestions": ["..."]
  },
  "root_folder_analysis": {
    "status": "Analyzed",
    "findings": {
      "config_found": true,
      "skill_count": 15,
      "local_skills": 12,
      "memory_word_count": 1200,
      "logs_size_mb": 45.3
    },
    "suggestions": ["..."]
  },
  "proposals": [
    "OpenRouter API key might be exhausted...",
    "MEMORY.md is large (5200 words)..."
  ]
}
```

## Examples

**Example 1: Daily health check**
*Scenario:* Run the optimizer as part of a morning routine to catch overnight issues.
*Action:* `python3 scripts/self_optimizer.py analyze`
*Outcome:* Reports 3 gateway restarts and suggests investigating configuration stability.

**Example 2: Automated monitoring with JSON output**
*Scenario:* Integrate into a cron job or monitoring pipeline.
*Action:* `python3 scripts/self_optimizer.py analyze --json`
*Outcome:* Structured JSON output that can be parsed by other tools or skills.

**Example 3: Analyzing user friction**
*Scenario:* After a session with many issues, analyze chat history to find patterns.
*Action:* `python3 scripts/self_optimizer.py analyze --chat-history-file ~/chat_export.json`
*Outcome:* Identifies 4 error mentions and 2 performance complaints, suggests optimizing model routing.
