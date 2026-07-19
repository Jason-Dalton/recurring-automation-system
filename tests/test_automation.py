import tempfile
import unittest
from pathlib import Path

from scripts import automation


def rebind_paths(root: Path) -> None:
    automation.REPO_ROOT = root
    automation.CONFIG_PATH = root / "config" / "settings.json"
    automation.LOGS_DIR = root / "logs"
    automation.MASTER_LOG = automation.LOGS_DIR / "master-project-log.md"
    automation.AUDIT_LOG = automation.LOGS_DIR / "automation-audit.md"
    automation.INTEGRATION_REQUESTS = automation.LOGS_DIR / "integration-requests.md"
    automation.PROJECTS_DIR = root / "projects"
    automation.ACTIVE_DIR = automation.PROJECTS_DIR / "active"
    automation.PAUSED_DIR = automation.PROJECTS_DIR / "paused"
    automation.COMPLETED_DIR = automation.PROJECTS_DIR / "completed"


class AutomationTests(unittest.TestCase):
    def test_init_creates_local_first_structure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rebind_paths(root)
            automation.cmd_init(None)
            self.assertTrue((root / "config" / "settings.json").exists())
            self.assertTrue((root / "projects" / "active").exists())
            self.assertTrue((root / "projects" / "paused").exists())
            self.assertTrue((root / "projects" / "completed").exists())
            self.assertTrue((root / "logs" / "master-project-log.md").exists())
            self.assertTrue((root / "logs" / "automation-audit.md").exists())

    def test_project_creation_and_progress_update(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rebind_paths(root)
            automation.ensure_layout()
            automation.load_config()
            automation.ensure_logs()

            project_id = "proj-test-000001"
            status_path = automation.create_project_status(
                project_id=project_id,
                name="Test Project",
                objective="Test objective",
                models=["GPT-4", "Claude"],
                priority=True,
            )
            automation.append_master(
                project_id=project_id,
                name="Test Project",
                objective="Test objective",
                models=["GPT-4", "Claude"],
                status_path=status_path,
            )
            automation.update_progress(
                project_id=project_id,
                accomplished="Completed module A",
                blockers="None",
                next_steps="Start module B",
                used_tools="GPT-4, Claude",
            )

            content = status_path.read_text(encoding="utf-8")
            self.assertIn("project_id: \"proj-test-000001\"", content)
            self.assertIn("## Progress Update - ", content)
            self.assertIn("- **Accomplished since last update:** Completed module A", content)
            self.assertIn("- **Models/tools actually used:** GPT-4, Claude", content)
            self.assertIn("proj-test-000001", automation.MASTER_LOG.read_text(encoding="utf-8"))

    def test_config_times_and_rule_controls(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rebind_paths(root)
            automation.ensure_layout()
            automation.load_config()
            automation.set_times(["09:00", "17:30"])
            config = automation.load_config()
            self.assertEqual(config["progress_prompt_times"], ["09:00", "17:30"])
            automation.pause_or_resume_rule("progress_prompt", "paused")
            self.assertEqual(automation.load_config()["rules"]["progress_prompt"], "paused")
            automation.pause_or_resume_rule("progress_prompt", "active")
            self.assertEqual(automation.load_config()["rules"]["progress_prompt"], "active")


if __name__ == "__main__":
    unittest.main()
