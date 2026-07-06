"""Tests for Opportunity CLI parsing."""

from __future__ import annotations

import argparse

from keprix_cli.subcommands.opportunity import build_opportunity_parser


def _parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    build_opportunity_parser(
        sub,
        cmd_new=lambda args: 0,
        cmd_run=lambda args: 0,
        cmd_phase=lambda args: 0,
        cmd_status=lambda args: 0,
        cmd_artifact=lambda args: 0,
        cmd_approve=lambda args: 0,
    )
    return parser


def test_cli_new_command_parses_title():
    args = _parser().parse_args(["opportunity", "new", "AI automation for estate agents"])
    assert args.opportunity_command == "new"
    assert args.title == "AI automation for estate agents"


def test_cli_phase_command_parses_phase():
    args = _parser().parse_args(["opportunity", "phase", "opp-abcd1234", "market_demand"])
    assert args.opportunity_command == "phase"
    assert args.phase == "market_demand"


def test_cli_artifact_command_parses_filename():
    args = _parser().parse_args(["opportunity", "artifact", "opp-abcd1234", "05-offer-doc.md"])
    assert args.opportunity_command == "artifact"
    assert args.filename == "05-offer-doc.md"
