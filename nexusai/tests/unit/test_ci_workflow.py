"""Regression guard for CI workflow context scoping (Phase 10R-CV R6).

A hosted C3 run was rejected at validation because the portability job set a
job-level ``env`` value using ``${{ runner.temp }}`` -- and the ``runner`` context is
only available in step contexts, not job-level ``env``. The whole workflow file was
invalidated, so no job ran.

This guard is deliberately narrow: it parses the CI workflow and asserts that no
job-level ``env`` value references a step-only context (``runner``, ``steps``,
``job``). It is not a general GitHub Actions validator.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"

# Contexts that are only populated once a runner/step is executing, and are therefore
# invalid inside job-level ``env`` (evaluated at graph-generation time).
_STEP_ONLY_CONTEXTS = ("runner", "steps", "job")

_CONTEXT_RE = re.compile(r"\$\{\{\s*([a-zA-Z_][\w-]*)\s*\.")


def _job_level_env_context_violations() -> list[str]:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    violations: list[str] = []
    for job_name, job in workflow["jobs"].items():
        for key, value in (job.get("env") or {}).items():
            for context in _CONTEXT_RE.findall(str(value)):
                if context in _STEP_ONLY_CONTEXTS:
                    violations.append(f"{job_name}.env.{key} -> {context}")
    return violations


class TestWorkflowJobLevelEnvContexts:
    def test_workflow_parses(self) -> None:
        assert _WORKFLOW.exists()
        assert "jobs" in yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))

    def test_no_job_level_env_uses_step_only_context(self) -> None:
        violations = _job_level_env_context_violations()
        assert not violations, (
            "Job-level env may not reference step-only contexts "
            f"(runner/steps/job): {violations}"
        )

    def test_detector_flags_a_synthetic_job_level_runner_reference(self) -> None:
        # Proves the guard catches the exact R5 defect shape.
        sample = {"jobs": {"p": {"env": {"ROOT": "${{ runner.temp }}/hk"}}}}
        found = [
            f"{j}.env.{k}"
            for j, job in sample["jobs"].items()
            for k, v in job["env"].items()
            for c in _CONTEXT_RE.findall(str(v))
            if c in _STEP_ONLY_CONTEXTS
        ]
        assert found == ["p.env.ROOT"]
