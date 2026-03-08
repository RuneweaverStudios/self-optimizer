#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


class SelfOptimizer:
    def __init__(self, logs_dir: Path, openclaw_home: Path):
        self.logs_dir = logs_dir
        self.openclaw_home = openclaw_home
        self.log_patterns = {
            "error": r"\b(Error|ERROR|exception|Exception|Fail):|\b(Failed to|error )",
            "restart": r"received SIGUSR1; restarting|received SIGTERM; shutting down",
            "gateway_status": r"gateway] listening on ws",
            "node_unavailable": r"remote bin probe skipped: node unavailable",
            "openrouter_403": r"403 Key limit exceeded",
            "config_change": r"config change detected; evaluating reload"
        }

    def _read_log_file(self, file_path, lines=500):
        try:
            if not os.path.exists(file_path):
                return []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()[-lines:]
        except (FileNotFoundError, PermissionError, IOError):
            return []
        except Exception as e:
            print(f"Warning: Error reading log file {file_path}: {e}", file=sys.stderr)
            return []

    def analyze_logs(self, minutes_back=60):
        try:
            gateway_log_path = os.path.join(self.logs_dir, "gateway.log")
            openclaw_log_path = os.path.join(self.logs_dir, "openclaw.log")

            all_logs = self._read_log_file(gateway_log_path)
            all_logs.extend(self._read_log_file(openclaw_log_path))
        except Exception as e:
            return {
                "errors": [f"Failed to read log files: {str(e)}"],
                "restarts": 0,
                "config_changes": 0,
                "openrouter_403s": 0,
                "node_unavailable_mentions": 0,
                "suggestions": ["Log file access error. Check file permissions and paths."]
            }

        recent_logs = []
        time_cutoff = datetime.now() - timedelta(minutes=minutes_back)

        for line in all_logs:
            try:
                # Try parsing ISO 8601 with timezone (Z)
                match_iso = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)", line)
                if match_iso:
                    timestamp_str = match_iso.group(1)
                    log_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    # Try parsing local time with timezone abbr (e.g., PST)
                    match_local = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \w{3})", line)
                    if match_local:
                        timestamp_str = match_local.group(1)
                        timestamp_without_tz = " ".join(timestamp_str.split(" ")[:-1])
                        log_time = datetime.strptime(timestamp_without_tz, "%Y-%m-%d %H:%M:%S")
                    else:
                        continue

                if log_time >= time_cutoff:
                    if "delivery recovery complete: 0 recovered, 0 failed, 0 skipped" not in line.lower():
                        recent_logs.append(line)
            except ValueError:
                continue

        analysis = {
            "errors": [],
            "restarts": 0,
            "config_changes": 0,
            "openrouter_403s": 0,
            "node_unavailable_mentions": 0,
            "suggestions": []
        }

        for line in recent_logs:
            if re.search(self.log_patterns["error"], line, re.IGNORECASE):
                analysis["errors"].append(line.strip())
            if re.search(self.log_patterns["restart"], line):
                analysis["restarts"] += 1
            if re.search(self.log_patterns["openrouter_403"], line):
                analysis["openrouter_403s"] += 1
            if re.search(self.log_patterns["node_unavailable"], line):
                analysis["node_unavailable_mentions"] += 1
            if re.search(self.log_patterns["config_change"], line):
                analysis["config_changes"] += 1

        if analysis["openrouter_403s"] > 0:
            analysis["suggestions"].append("OpenRouter API key might be exhausted or improperly configured. Check https://openrouter.ai/settings/keys.")
        if analysis["restarts"] >= 2:
            analysis["suggestions"].append("Frequent gateway restarts detected. Investigate recent configuration changes or system instability.")
        if analysis["errors"]:
            analysis["suggestions"].append(f"Found {len(analysis['errors'])} error(s) in logs. Review specific error messages for actionable insights.")
        if analysis["node_unavailable_mentions"] > 0:
            analysis["suggestions"].append(f"Node unavailable mentions detected ({analysis['node_unavailable_mentions']}). Ensure companion app is running and connected.")
        if analysis["config_changes"] >= 3:
            analysis["suggestions"].append("Multiple configuration changes detected. Review openclaw.json for unintended changes.")

        return analysis

    def analyze_chat_history(self, chat_history_data: List[Dict[str, Any]], lookback_minutes=120):
        if not chat_history_data:
            return {"status": "No chat history data provided", "issues_summary": {}, "suggestions": []}

        try:
            chat_issues: Dict[str, int] = Counter()
            suggestions: List[str] = []

            problem_keywords = {
                "error": ["error", "fail", "issue", "problem", "bug"],
                "confusion": ["confused", "don't understand", "unclear", "huh?"],
                "performance": ["slow", "lag", "cost", "expensive", "quota"],
                "unavailability": ["unavailable", "not working", "disconnected"],
                "delegation": ["subagent failed", "spawn failed", "agent failed"]
            }

            time_cutoff = datetime.now() - timedelta(minutes=lookback_minutes)

            for entry in chat_history_data:
                try:
                    if not isinstance(entry, dict):
                        continue
                    if 'message' in entry and entry.get('role') == 'user':
                        timestamp = entry.get('timestamp', '')
                        if not timestamp:
                            continue
                        try:
                            message_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            continue
                        if message_time < time_cutoff:
                            continue

                        text = str(entry.get('message', '')).lower()
                        for issue_type, keywords in problem_keywords.items():
                            for keyword in keywords:
                                if keyword in text:
                                    chat_issues[issue_type] += 1
                except (KeyError, AttributeError, ValueError):
                    continue

            if chat_issues.get("error", 0) > 0:
                suggestions.append(f"Recurring errors detected in chat history ({chat_issues['error']} mentions from user). Investigate common error patterns.")
            if chat_issues.get("confusion", 0) > 0:
                suggestions.append(f"User confusion detected ({chat_issues['confusion']} mentions). Consider clarifying responses or providing more context.")
            if chat_issues.get("performance", 0) > 0:
                suggestions.append(f"Performance/cost concerns detected ({chat_issues['performance']} mentions). Optimize resource usage or suggest cheaper models.")
            if chat_issues.get("unavailability", 0) > 0:
                suggestions.append(f"Tool/service unavailability mentioned ({chat_issues['unavailability']} mentions). Check external service statuses.")
            if chat_issues.get("delegation", 0) > 0:
                suggestions.append(f"Sub-agent/delegation failures mentioned ({chat_issues['delegation']} mentions). Review agent swarm routing.")

            return {"status": "Analyzed", "issues_summary": dict(chat_issues), "suggestions": suggestions}

        except Exception as e:
            return {
                "status": f"Error analyzing chat history: {str(e)}",
                "issues_summary": {},
                "suggestions": ["Chat history analysis failed. Check data format."]
            }

    def analyze_root_folder(self):
        """Scan the OpenClaw home directory for optimization opportunities."""
        suggestions = []
        findings = {}

        # Check openclaw.json config
        config_path = self.openclaw_home / "openclaw.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                findings["config_found"] = True

                # Check for common config issues
                skills = config.get("skills", [])
                findings["skill_count"] = len(skills) if isinstance(skills, list) else 0

                if findings["skill_count"] == 0:
                    suggestions.append("No skills configured in openclaw.json. Consider adding skills to extend functionality.")
                elif findings["skill_count"] > 20:
                    suggestions.append(f"Large number of skills ({findings['skill_count']}) configured. Consider disabling unused skills for faster startup.")

                # Check for model configuration
                if "model" not in config and "defaultModel" not in config:
                    suggestions.append("No default model configured. Setting a default model in openclaw.json can improve response consistency.")

            except json.JSONDecodeError:
                findings["config_found"] = True
                findings["config_valid"] = False
                suggestions.append("openclaw.json contains invalid JSON. Fix the syntax to prevent configuration errors.")
            except Exception as e:
                findings["config_error"] = str(e)
        else:
            findings["config_found"] = False
            suggestions.append("No openclaw.json found. Run `openclaw init` to set up your configuration.")

        # Check MEMORY.md
        memory_path = self.openclaw_home / "MEMORY.md"
        if memory_path.exists():
            try:
                content = memory_path.read_text(encoding="utf-8", errors="ignore")
                word_count = len(content.split())
                findings["memory_word_count"] = word_count
                if word_count > 5000:
                    suggestions.append(f"MEMORY.md is large ({word_count} words). Consider summarizing or archiving older entries for faster context loading.")
                elif word_count == 0:
                    suggestions.append("MEMORY.md is empty. Recording key learnings helps the agent improve over time.")
            except Exception:
                pass
        else:
            findings["memory_exists"] = False

        # Check skills directory
        skills_dir = self.openclaw_home / "skills"
        if skills_dir.exists() and skills_dir.is_dir():
            skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            findings["local_skills"] = len(skill_dirs)

            # Check for skills missing _meta.json
            missing_meta = []
            for sd in skill_dirs:
                if not (sd / "_meta.json").exists():
                    missing_meta.append(sd.name)
            if missing_meta:
                suggestions.append(f"Skills missing _meta.json: {', '.join(missing_meta[:5])}. Add metadata for proper skill registration.")
                findings["skills_missing_meta"] = missing_meta
        else:
            findings["local_skills"] = 0

        # Check logs directory size
        if self.logs_dir.exists():
            total_size = 0
            for f in self.logs_dir.iterdir():
                if f.is_file():
                    total_size += f.stat().st_size
            findings["logs_size_mb"] = round(total_size / (1024 * 1024), 2)
            if findings["logs_size_mb"] > 100:
                suggestions.append(f"Logs directory is {findings['logs_size_mb']}MB. Consider rotating or cleaning old logs.")

        status = "Analyzed" if findings else "No OpenClaw home directory found"
        return {"status": status, "findings": findings, "suggestions": suggestions}

    def propose_improvements(self, chat_history_data: Optional[List[Dict[str, Any]]] = None):
        try:
            log_analysis = self.analyze_logs()
        except Exception as e:
            log_analysis = {
                "errors": [f"Log analysis failed: {str(e)}"],
                "restarts": 0,
                "config_changes": 0,
                "openrouter_403s": 0,
                "node_unavailable_mentions": 0,
                "suggestions": ["Log analysis encountered an error. Check system logs for details."]
            }

        try:
            chat_history_analysis = self.analyze_chat_history(chat_history_data=chat_history_data or [])
        except Exception as e:
            chat_history_analysis = {
                "status": f"Error: {str(e)}",
                "issues_summary": {},
                "suggestions": ["Chat history analysis encountered an error."]
            }

        try:
            root_folder_analysis = self.analyze_root_folder()
        except Exception as e:
            root_folder_analysis = {
                "status": f"Error: {str(e)}",
                "findings": {},
                "suggestions": []
            }

        proposals = []
        if log_analysis.get("suggestions"):
            proposals.extend(log_analysis["suggestions"])
        if chat_history_analysis.get("suggestions"):
            proposals.extend(chat_history_analysis["suggestions"])
        if root_folder_analysis.get("suggestions"):
            proposals.extend(root_folder_analysis["suggestions"])

        if not proposals:
            proposals.append("No critical issues found. Consider optimizing frequently used skills or automating routine checks.")

        overall_report = {
            "log_analysis": log_analysis,
            "chat_history_analysis": chat_history_analysis,
            "root_folder_analysis": root_folder_analysis,
            "proposals": proposals
        }
        return overall_report


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Self-Optimizer Skill.")
    parser.add_argument("command", choices=["analyze"], default="analyze", nargs="?", help="The command to run (default: analyze).")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    parser.add_argument("--chat-history-file", type=str, help="Path to a JSON file containing chat history data.")
    args = parser.parse_args()

    # Determine logs directory based on OPENCLAW_HOME
    openclaw_home = Path(os.environ.get("OPENCLAW_HOME", Path.home() / ".openclaw"))
    logs_dir = openclaw_home / "logs"

    optimizer = SelfOptimizer(logs_dir, openclaw_home)

    if args.command == "analyze":
        chat_history_data = []
        if args.chat_history_file:
            try:
                with open(args.chat_history_file, "r") as f:
                    chat_history_data = json.load(f)
            except FileNotFoundError:
                print(f"Error: Chat history file not found: {args.chat_history_file}", file=sys.stderr)
                sys.exit(1)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in chat history file: {args.chat_history_file}", file=sys.stderr)
                sys.exit(1)

        report = optimizer.propose_improvements(chat_history_data=chat_history_data)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("\n--- OpenClaw Self-Optimization Report ---")
            print("\nLog Analysis:")
            print(f"  Recent Errors: {len(report['log_analysis']['errors'])} detected")
            for error in report['log_analysis']['errors'][:10]:
                print(f"    - {error}")
            if len(report['log_analysis']['errors']) > 10:
                print(f"    ... and {len(report['log_analysis']['errors']) - 10} more")
            print(f"  Gateway Restarts: {report['log_analysis']['restarts']} detected")
            print(f"  OpenRouter 403s: {report['log_analysis']['openrouter_403s']} detected")
            print(f"  Node Unavailable Mentions: {report['log_analysis']['node_unavailable_mentions']} detected")
            print(f"  Config Changes: {report['log_analysis']['config_changes']} detected")

            print("\nChat History Analysis:")
            print(f"  Status: {report['chat_history_analysis']['status']}")
            if report['chat_history_analysis'].get('suggestions'):
                print("  Suggestions:")
                for suggestion in report['chat_history_analysis']['suggestions']:
                    print(f"    - {suggestion}")

            print("\nRoot Folder Analysis:")
            print(f"  Status: {report['root_folder_analysis']['status']}")
            findings = report['root_folder_analysis'].get('findings', {})
            if findings:
                if 'config_found' in findings:
                    print(f"  Config found: {findings['config_found']}")
                if 'skill_count' in findings:
                    print(f"  Configured skills: {findings['skill_count']}")
                if 'local_skills' in findings:
                    print(f"  Local skills: {findings['local_skills']}")
                if 'memory_word_count' in findings:
                    print(f"  MEMORY.md size: {findings['memory_word_count']} words")
                if 'logs_size_mb' in findings:
                    print(f"  Logs size: {findings['logs_size_mb']}MB")
            if report['root_folder_analysis'].get('suggestions'):
                print("  Suggestions:")
                for suggestion in report['root_folder_analysis']['suggestions']:
                    print(f"    - {suggestion}")

            print("\n--- Self-Improvement Proposals ---")
            if report['proposals']:
                for i, proposal in enumerate(report['proposals']):
                    print(f"  {i + 1}. {proposal}")
            else:
                print("  No specific proposals at this time.")

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
