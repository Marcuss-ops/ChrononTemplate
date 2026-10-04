"""kit — shared library for ChrononTemplate showcase suite scripts.

One place for workspace/CLI discovery, render-plan authoring, the
validate->render->manifest->upload pipeline and the Drive upload helpers,
so a new suite script contains only its creative content.
"""

from .drive import link_for, refresh_token, upload_file, upload_many
from .paths import CLI_CANDIDATES, Workspace, find_workspace
from .plan import Canvas, Plan, SCHEMA, SCHEMA_VERSION, fade, track
from .pipeline import Suite, SuiteItem, add_pipeline_args, run_suite

__all__ = [
    "CLI_CANDIDATES",
    "Canvas",
    "Plan",
    "SCHEMA",
    "SCHEMA_VERSION",
    "Suite",
    "SuiteItem",
    "Workspace",
    "add_pipeline_args",
    "fade",
    "find_workspace",
    "link_for",
    "refresh_token",
    "run_suite",
    "track",
    "upload_file",
    "upload_many",
]
