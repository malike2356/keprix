from __future__ import annotations

import argparse


def parser(description: str) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--database-url", default=None)
    return result


def require_data(minimum: int, actual: int) -> None:
    if actual < minimum:
        raise SystemExit(f"Not enough labeled records: need {minimum}, found {actual}")
