"""CLI entrypoint for SaioMusic."""

from __future__ import annotations


def main() -> int:
    try:
        from saio_music.ui.main_window import run
    except ModuleNotFoundError:
        print("UI dependency missing. Install with: pip install -e .[dev]")
        return 1

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
