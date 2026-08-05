"""CLI commands for structured workspace memory."""

from __future__ import annotations

import argparse
import json
import sys


def register_cli(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="workspace_command", required=True)

    init = sub.add_parser("init", help="Create a structured workspace")
    init.add_argument("--template", default="knowledge_pipeline")
    init.add_argument("--name", required=True)

    index = sub.add_parser("index", help="Regenerate workspace index.md files")
    index.add_argument("--name", required=True)
    index.add_argument("--folder", default=None)

    templates = sub.add_parser("templates", help="List workspace templates")
    _ = templates

    parser.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> int:
    from keprix.workspace.index_generator import WorkspaceIndexer
    from keprix.workspace.template_presets import create_workspace, list_templates, workspace_root

    if args.workspace_command == "templates":
        print(json.dumps([template.to_dict() for template in list_templates()], indent=2))
        return 0
    if args.workspace_command == "init":
        try:
            workspace = create_workspace(args.name, args.template)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(workspace, indent=2))
        return 0
    if args.workspace_command == "index":
        root = workspace_root(args.name)
        if not root.exists():
            print(f"workspace not found: {root}", file=sys.stderr)
            return 1
        indexer = WorkspaceIndexer(root)
        if args.folder:
            content = indexer.update_index(args.folder)
            print(content)
        else:
            updated = indexer.reindex_all()
            print(json.dumps({"updated": [str(path) for path in updated]}, indent=2))
        return 0
    return 2
