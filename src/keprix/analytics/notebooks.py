"""Notebook export helpers."""

from __future__ import annotations


def export_notebook(code_cells: list[str], markdown_cells: list[str] | None = None) -> dict:
    cells = []
    for text in markdown_cells or []:
        cells.append({"cell_type": "markdown", "source": text.splitlines(True), "metadata": {}})
    for code in code_cells:
        cells.append({"cell_type": "code", "source": code.splitlines(True), "metadata": {}, "outputs": []})
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
