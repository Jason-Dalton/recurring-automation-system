# Recurring Automation System (Local-First)

This repository provides a fully local, offline-first recurring automation system for personal AI project management.

## What it does

- Creates and maintains a master Markdown project log
- Creates one Markdown status file per project (single source of truth)
- Supports twice-daily progress prompts (configurable times)
- Supports work-session initialization with model checklist
- Proposes context-aware assignments from recent/priority project state
- Logs all automation decisions to a human-readable audit trail
- Keeps project files separated by lifecycle state (`active`, `paused`, `completed`)
- Provides local backup reminders
- Provides config controls to review schedules and pause/resume rules
- Includes uninstall steps without deleting your project data

## Quick start

```bash
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py init
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config show
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py project new \
  --name "Example AI Project" \
  --objective "Build local reporting workflow" \
  --models GPT-4 Claude \
  --priority
```

## Core command examples

```bash
# Update configured prompt times (exactly two daily times)
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config set-times --times 12:00 18:00

# Run interactive progress prompt for a project
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py prompt progress --project-id <project-id>

# Start a work session with selected models
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py session start --models GPT-4 Gemini

# Pause/resume a rule
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config pause-rule --rule progress_prompt
python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config resume-rule --rule progress_prompt
```

## Scheduling twice-daily prompts (local-only)

Use your local scheduler (for example `cron`) to trigger prompts at your configured times:

```cron
0 12 * * * cd /home/runner/work/recurring-automation-system/recurring-automation-system && python3 scripts/automation.py prompt progress --project-id <project-id>
0 18 * * * cd /home/runner/work/recurring-automation-system/recurring-automation-system && python3 scripts/automation.py prompt progress --project-id <project-id>
```

## External integrations policy

- Core functionality is local-first and offline by default.
- This project does not call external services.
- If you want to integrate an external system, create an explicit opt-in request in `logs/integration-requests.md` documenting:
  - what data would be shared
  - why it is needed
  - your explicit approval

## Disable / uninstall without data loss

1. Disable local scheduler entries (cron/Task Scheduler/launchd).
2. Optionally pause all rules:
   ```bash
   python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config pause-rule --rule progress_prompt
   python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config pause-rule --rule work_session_checklist
   python3 /home/runner/work/recurring-automation-system/recurring-automation-system/scripts/automation.py config pause-rule --rule assignment_suggestions
   ```
3. Keep `projects/` and `logs/` for retained history.
4. Remove only automation code if desired (`scripts/automation.py`) after backup.
