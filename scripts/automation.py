#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "settings.json"
LOGS_DIR = REPO_ROOT / "logs"
MASTER_LOG = LOGS_DIR / "master-project-log.md"
AUDIT_LOG = LOGS_DIR / "automation-audit.md"
INTEGRATION_REQUESTS = LOGS_DIR / "integration-requests.md"
PROJECTS_DIR = REPO_ROOT / "projects"
ACTIVE_DIR = PROJECTS_DIR / "active"
PAUSED_DIR = PROJECTS_DIR / "paused"
COMPLETED_DIR = PROJECTS_DIR / "completed"

RULES = {"progress_prompt", "work_session_checklist", "assignment_suggestions"}
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass
class ProjectInfo:
    project_id: str
    path: Path
    content: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts() -> str:
    return utc_now().isoformat()


def ensure_layout() -> None:
    (REPO_ROOT / "config").mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    PAUSED_DIR.mkdir(parents=True, exist_ok=True)
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)


def default_config() -> dict:
    return {
        "local_first": True,
        "progress_prompt_times": ["12:00", "18:00"],
        "backup_reminder_enabled": True,
        "work_session_detection": {
            "mode": "manual_trigger",
            "idle_threshold_minutes": 60,
            "app_hints": [],
        },
        "rules": {
            "progress_prompt": "active",
            "work_session_checklist": "active",
            "assignment_suggestions": "active",
        },
    }


def load_config() -> dict:
    ensure_layout()
    if not CONFIG_PATH.exists():
        config = default_config()
        save_config(config)
        return config
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def ensure_logs() -> None:
    write_if_missing(
        MASTER_LOG,
        """---
title: Master AI Project Log
created_at: "{created_at}"
---

# Master AI Project Log

| Project ID | Project Name | Started At (UTC) | Objective | Initial Models/Tools | Status File |
|---|---|---|---|---|---|
""".format(created_at=ts()),
    )
    write_if_missing(
        AUDIT_LOG,
        """---
title: Automation Audit Trail
created_at: "{created_at}"
---

# Automation Audit Trail
""".format(created_at=ts()),
    )
    write_if_missing(
        INTEGRATION_REQUESTS,
        """---
title: External Integration Requests (Opt-In)
created_at: "{created_at}"
---

# External Integration Requests (Opt-In)
""".format(created_at=ts()),
    )


def audit(message: str) -> None:
    ensure_logs()
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n## {ts()}\n- {message}\n")


def create_project_status(project_id: str, name: str, objective: str, models: List[str], priority: bool) -> Path:
    path = ACTIVE_DIR / f"{project_id}.md"
    model_str = ", ".join(models) if models else "Unspecified"
    content = f"""---
project_id: "{project_id}"
project_name: "{name}"
created_at: "{ts()}"
status: "active"
priority: {str(priority).lower()}
objective: "{objective}"
initial_models_tools:
{chr(10).join(f'  - "{m}"' for m in models) if models else '  - "Unspecified"'}
---

# {name}

## Objective
{objective}

## Initial Model/Tool Selection
- {model_str}

## Actionable Items
- [ ] Add first implementation milestone
- [ ] Confirm next update checkpoint

## Chronological Project Log
"""
    path.write_text(content, encoding="utf-8")
    return path


def append_master(project_id: str, name: str, objective: str, models: List[str], status_path: Path) -> None:
    ensure_logs()
    models_text = ", ".join(models) if models else "Unspecified"
    with MASTER_LOG.open("a", encoding="utf-8") as f:
        f.write(
            f"| {project_id} | {name} | {ts()} | {objective.replace('|', '/')} | "
            f"{models_text.replace('|', '/')} | {status_path.relative_to(REPO_ROOT)} |\n"
        )


def find_project(project_id: str) -> ProjectInfo:
    for state_dir in (ACTIVE_DIR, PAUSED_DIR, COMPLETED_DIR):
        p = state_dir / f"{project_id}.md"
        if p.exists():
            return ProjectInfo(project_id=project_id, path=p, content=p.read_text(encoding="utf-8"))
    raise SystemExit(f"Project not found: {project_id}")


def update_progress(project_id: str, accomplished: str, blockers: str, next_steps: str, used_tools: str) -> None:
    proj = find_project(project_id)
    with proj.path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n## Progress Update - {ts()}\n"
            f"- **Accomplished since last update:** {accomplished}\n"
            f"- **Blockers or challenges:** {blockers}\n"
            f"- **Next planned steps:** {next_steps}\n"
            f"- **Models/tools actually used:** {used_tools}\n"
        )
    audit(f"Progress update appended for project {project_id}.")


def extract_priority(content: str) -> bool:
    return re.search(r"^priority:\s*true\s*$", content, re.MULTILINE) is not None


def extract_last_next_steps(content: str) -> str:
    matches = re.findall(r"- \*\*Next planned steps:\*\* (.+)", content)
    if matches:
        return matches[-1].strip()
    return "No prior next steps recorded."


def list_active_projects() -> List[ProjectInfo]:
    projects: List[ProjectInfo] = []
    for p in sorted(ACTIVE_DIR.glob("*.md")):
        projects.append(ProjectInfo(project_id=p.stem, path=p, content=p.read_text(encoding="utf-8")))
    return projects


def start_session(models: List[str]) -> None:
    selected = ", ".join(models) if models else "None selected"
    projects = list_active_projects()
    priority = [p for p in projects if extract_priority(p.content)]
    recent = sorted(projects, key=lambda p: p.path.stat().st_mtime, reverse=True)[:3]

    print("Work session initialized.")
    print(f"Selected models: {selected}")
    print("\nSuggested assignments:")

    if priority:
        print("\nPriority projects:")
        for p in priority:
            print(f"- {p.project_id}: {extract_last_next_steps(p.content)}")
    if recent:
        print("\nRecent active projects with incomplete status:")
        for p in recent:
            print(f"- {p.project_id}: {extract_last_next_steps(p.content)}")
    if not projects:
        print("- No active projects found. Start one with: project new")

    audit(f"Work session checklist completed. Models selected: {selected}.")


def move_project(project_id: str, dest: str) -> None:
    proj = find_project(project_id)
    destination = {"active": ACTIVE_DIR, "paused": PAUSED_DIR, "completed": COMPLETED_DIR}[dest] / proj.path.name
    proj.path.replace(destination)
    content = destination.read_text(encoding="utf-8")
    updated = re.sub(r'^status:\s*".*?"\s*$', f'status: "{dest}"', content, flags=re.MULTILINE)
    destination.write_text(updated, encoding="utf-8")
    audit(f"Project {project_id} moved to {dest}.")


def show_config() -> None:
    config = load_config()
    print(json.dumps(config, indent=2))


def validate_times(times: List[str]) -> None:
    if len(times) != 2:
        raise SystemExit("Exactly two times are required (HH:MM HH:MM).")
    if not all(TIME_PATTERN.match(t) for t in times):
        raise SystemExit("Invalid time format. Use HH:MM in 24-hour format.")


def set_times(times: List[str]) -> None:
    validate_times(times)
    config = load_config()
    config["progress_prompt_times"] = times
    save_config(config)
    audit(f"Prompt schedule updated to {times[0]} and {times[1]} UTC/local user scheduling context.")


def pause_or_resume_rule(rule: str, status: str) -> None:
    if rule not in RULES:
        raise SystemExit(f"Unknown rule '{rule}'. Valid values: {', '.join(sorted(RULES))}")
    config = load_config()
    config["rules"][rule] = status
    save_config(config)
    audit(f"Rule '{rule}' changed to '{status}'.")


def progress_prompt(project_id: str) -> None:
    config = load_config()
    if config["rules"].get("progress_prompt") != "active":
        raise SystemExit("progress_prompt rule is paused.")
    print("What did you accomplish since the last update?")
    accomplished = input("> ").strip()
    print("What blockers or challenges did you encounter?")
    blockers = input("> ").strip()
    print("What are your next planned steps?")
    next_steps = input("> ").strip()
    print("What models or tools did you actually use?")
    used_tools = input("> ").strip()
    update_progress(project_id, accomplished, blockers, next_steps, used_tools)
    if config.get("backup_reminder_enabled", True):
        backup_reminder()


def backup_reminder() -> None:
    msg = (
        "Backup reminder: create or verify a local backup copy of projects/ and logs/ "
        "to avoid data loss."
    )
    print(msg)
    audit(msg)


def request_integration(name: str, data_shared: str, purpose: str) -> None:
    ensure_logs()
    with INTEGRATION_REQUESTS.open("a", encoding="utf-8") as f:
        f.write(
            f"\n## {ts()}\n"
            f"- Integration: {name}\n"
            f"- Data to share: {data_shared}\n"
            f"- Purpose: {purpose}\n"
            f"- Approval status: pending explicit user opt-in\n"
        )
    audit(f"External integration request logged for {name} (pending approval).")


def cmd_init(_: argparse.Namespace) -> None:
    ensure_layout()
    load_config()
    ensure_logs()
    audit("System initialized in local-first mode.")
    print("Initialized local recurring automation system.")


def cmd_project_new(args: argparse.Namespace) -> None:
    ensure_layout()
    load_config()
    ensure_logs()
    project_id = f"proj-{utc_now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
    models = args.models or []
    status_path = create_project_status(project_id, args.name, args.objective, models, args.priority)
    append_master(project_id, args.name, args.objective, models, status_path)
    audit(f"New project created: {project_id} ({args.name}).")
    print(project_id)


def cmd_project_move(args: argparse.Namespace) -> None:
    move_project(args.project_id, args.to)
    print(f"Moved {args.project_id} to {args.to}.")


def cmd_update_progress(args: argparse.Namespace) -> None:
    update_progress(args.project_id, args.accomplished, args.blockers, args.next_steps, args.used_tools)
    print(f"Updated {args.project_id}.")


def cmd_session_start(args: argparse.Namespace) -> None:
    config = load_config()
    if config["rules"].get("work_session_checklist") != "active":
        raise SystemExit("work_session_checklist rule is paused.")
    start_session(args.models or [])


def cmd_config_show(_: argparse.Namespace) -> None:
    show_config()


def cmd_config_set_times(args: argparse.Namespace) -> None:
    set_times(args.times)
    print("Prompt times updated.")


def cmd_config_pause_rule(args: argparse.Namespace) -> None:
    pause_or_resume_rule(args.rule, "paused")
    print(f"Paused rule: {args.rule}")


def cmd_config_resume_rule(args: argparse.Namespace) -> None:
    pause_or_resume_rule(args.rule, "active")
    print(f"Resumed rule: {args.rule}")


def cmd_prompt_progress(args: argparse.Namespace) -> None:
    progress_prompt(args.project_id)


def cmd_prompt_backup(_: argparse.Namespace) -> None:
    backup_reminder()


def cmd_integration_request(args: argparse.Namespace) -> None:
    request_integration(args.name, args.data_shared, args.purpose)
    print(f"Logged integration request for {args.name}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-first recurring AI project automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.set_defaults(func=cmd_init)

    p_project = sub.add_parser("project")
    p_project_sub = p_project.add_subparsers(dest="project_command", required=True)

    p_project_new = p_project_sub.add_parser("new")
    p_project_new.add_argument("--name", required=True)
    p_project_new.add_argument("--objective", required=True)
    p_project_new.add_argument("--models", nargs="*", default=[])
    p_project_new.add_argument("--priority", action="store_true")
    p_project_new.set_defaults(func=cmd_project_new)

    p_project_move = p_project_sub.add_parser("move")
    p_project_move.add_argument("--project-id", required=True)
    p_project_move.add_argument("--to", required=True, choices=["active", "paused", "completed"])
    p_project_move.set_defaults(func=cmd_project_move)

    p_update = sub.add_parser("update")
    p_update_sub = p_update.add_subparsers(dest="update_command", required=True)
    p_update_progress = p_update_sub.add_parser("progress")
    p_update_progress.add_argument("--project-id", required=True)
    p_update_progress.add_argument("--accomplished", required=True)
    p_update_progress.add_argument("--blockers", required=True)
    p_update_progress.add_argument("--next-steps", required=True)
    p_update_progress.add_argument("--used-tools", required=True)
    p_update_progress.set_defaults(func=cmd_update_progress)

    p_session = sub.add_parser("session")
    p_session_sub = p_session.add_subparsers(dest="session_command", required=True)
    p_session_start = p_session_sub.add_parser("start")
    p_session_start.add_argument("--models", nargs="*", default=[])
    p_session_start.set_defaults(func=cmd_session_start)

    p_config = sub.add_parser("config")
    p_config_sub = p_config.add_subparsers(dest="config_command", required=True)
    p_config_show = p_config_sub.add_parser("show")
    p_config_show.set_defaults(func=cmd_config_show)
    p_config_times = p_config_sub.add_parser("set-times")
    p_config_times.add_argument("--times", nargs=2, required=True)
    p_config_times.set_defaults(func=cmd_config_set_times)
    p_config_pause = p_config_sub.add_parser("pause-rule")
    p_config_pause.add_argument("--rule", required=True)
    p_config_pause.set_defaults(func=cmd_config_pause_rule)
    p_config_resume = p_config_sub.add_parser("resume-rule")
    p_config_resume.add_argument("--rule", required=True)
    p_config_resume.set_defaults(func=cmd_config_resume_rule)

    p_prompt = sub.add_parser("prompt")
    p_prompt_sub = p_prompt.add_subparsers(dest="prompt_command", required=True)
    p_prompt_progress = p_prompt_sub.add_parser("progress")
    p_prompt_progress.add_argument("--project-id", required=True)
    p_prompt_progress.set_defaults(func=cmd_prompt_progress)
    p_prompt_backup = p_prompt_sub.add_parser("backup-reminder")
    p_prompt_backup.set_defaults(func=cmd_prompt_backup)

    p_integration = sub.add_parser("integration")
    p_integration_sub = p_integration.add_subparsers(dest="integration_command", required=True)
    p_integration_request = p_integration_sub.add_parser("request")
    p_integration_request.add_argument("--name", required=True)
    p_integration_request.add_argument("--data-shared", required=True)
    p_integration_request.add_argument("--purpose", required=True)
    p_integration_request.set_defaults(func=cmd_integration_request)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
