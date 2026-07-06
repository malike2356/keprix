"""Opportunity Engine CLI subcommand parsers."""

from __future__ import annotations

from typing import Callable


def build_opportunity_parser(
    subparsers,
    *,
    cmd_new: Callable,
    cmd_run: Callable,
    cmd_phase: Callable,
    cmd_status: Callable,
    cmd_artifact: Callable,
    cmd_approve: Callable,
) -> None:
    opp_parser = subparsers.add_parser(
        "opportunity",
        help="Opportunity Engine: discover and validate market opportunities",
        description=(
            "Create opportunity workspaces, run validation playbooks, "
            "and manage approval gates for launch actions."
        ),
    )
    opp_sub = opp_parser.add_subparsers(dest="opportunity_command", required=True)

    new_parser = opp_sub.add_parser("new", help="Create a new opportunity workspace")
    new_parser.add_argument("title", help="Opportunity title")
    new_parser.add_argument("--niche", default=None, help="Target niche")
    new_parser.add_argument("--market", default=None, help="Target market")
    new_parser.add_argument("--goal", default=None, help="Business goal")
    new_parser.add_argument("--workspace-id", default="default", help="Workspace ID")
    new_parser.set_defaults(func=cmd_new)

    run_parser = opp_sub.add_parser("run", help="Run the full opportunity pipeline")
    run_parser.add_argument("opportunity_id", help="Opportunity ID (opp-xxxxxxxx)")
    run_parser.add_argument(
        "--pause-on-approval",
        action="store_true",
        help="Stop pipeline when approval is required",
    )
    run_parser.set_defaults(func=cmd_run)

    phase_parser = opp_sub.add_parser("phase", help="Run a single pipeline phase")
    phase_parser.add_argument("opportunity_id", help="Opportunity ID")
    phase_parser.add_argument("phase", help="Phase name (e.g. market_demand)")
    phase_parser.set_defaults(func=cmd_phase)

    status_parser = opp_sub.add_parser("status", help="Show opportunity status")
    status_parser.add_argument("opportunity_id", help="Opportunity ID")
    status_parser.set_defaults(func=cmd_status)

    artifact_parser = opp_sub.add_parser("artifact", help="Print an opportunity artifact")
    artifact_parser.add_argument("opportunity_id", help="Opportunity ID")
    artifact_parser.add_argument("filename", help="Artifact filename (e.g. 05-offer-doc.md)")
    artifact_parser.add_argument("--json", action="store_true", help="Output JSON wrapper")
    artifact_parser.set_defaults(func=cmd_artifact)

    approve_parser = opp_sub.add_parser("approve", help="Approve or reject a gated action")
    approve_parser.add_argument("opportunity_id", help="Opportunity ID")
    approve_parser.add_argument("approval_id", help="Approval ID")
    approve_parser.add_argument("--reject", action="store_true", help="Reject instead of approve")
    approve_parser.set_defaults(func=cmd_approve)
