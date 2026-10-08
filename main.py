"""
Run the full red-flag screener pipeline, start to finish, in one command.

This file does not calculate anything itself. It only runs the existing
scripts in src/ (and the chart notebook) in the right order, one after
another, and stops with a clear message if any step fails. Each step is
a separate process, so this file never imports or changes any of the
finance/scoring code.

Usage (from the project root, with the virtual environment activated):

    python main.py
        Runs all 9 steps, including re-downloading financial data from
        Yahoo Finance (step 2, which is slow: ~20 companies, ~1.5s pause
        each).

    python main.py --skip-fetch
        Skips step 2 and reuses whatever is already saved in data/raw/.
        Use this once you already have a successful download, so you are
        not waiting on the network (or hitting Yahoo Finance's rate
        limits) every time you re-run the pipeline.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# The folder this file lives in, i.e. the project root. Every step below
# is run with this as its working directory, so the pipeline works the
# same way no matter where main.py is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent

TOTAL_STEPS = 9


def parse_args():
    """Read command-line flags. Only --skip-fetch exists for now."""
    parser = argparse.ArgumentParser(
        description="Run the Nifty Pharma red-flag screener pipeline end to end."
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Reuse the existing data/raw/ files instead of re-downloading "
             "from Yahoo Finance.",
    )
    return parser.parse_args()


def run_step(step_num, label, command):
    """
    Run one pipeline step as a separate process and print a status line.

    command is a list of strings, e.g. [sys.executable, "src/ratios.py"].
    We never build a command as one shell string (and never pass
    shell=True) because that would need careful quoting on Windows;
    a plain list of arguments sidesteps that entirely.

    If the step fails (non-zero exit code), we print what it was and its
    captured output, then stop the whole pipeline immediately - later
    steps all depend on earlier ones, so continuing would only produce
    confusing follow-on failures.
    """
    print(f"[{step_num}/{TOTAL_STEPS}] {label}...")

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # never let an odd byte from a child process crash main.py itself
    )

    if result.returncode != 0:
        print(f"[{step_num}/{TOTAL_STEPS}] {label}... FAILED")
        print()
        print(f"Step {step_num} failed. Command: {' '.join(command)}")
        print()
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)
        sys.exit(1)

    print(f"[{step_num}/{TOTAL_STEPS}] {label}... done")


def run_fetch_step(skip_fetch):
    """
    Step 2: download financial statements from Yahoo Finance.

    src/fetch_financials.py has no command-line flags of its own (its
    whole download loop runs directly under its own
    if __name__ == "__main__" block), so "skipping" it means main.py
    simply does not call it at all - there is nothing in that script to
    call selectively.
    """
    step_num = 2
    label = "Fetching financials from Yahoo Finance (slow: ~20 tickers)"

    if not skip_fetch:
        run_step(step_num, label, [sys.executable, "src/fetch_financials.py"])
        return

    # --skip-fetch was given. Check data/raw actually has something to
    # reuse, so a missing/empty folder fails clearly right here, instead
    # of causing a confusing error three steps later inside
    # clean_financials.py.
    raw_dir = PROJECT_ROOT / "data" / "raw"
    has_files = raw_dir.is_dir() and any(raw_dir.iterdir())

    if not has_files:
        print(f"[{step_num}/{TOTAL_STEPS}] {label}... FAILED")
        print()
        print(f"--skip-fetch was given, but {raw_dir} is missing or empty.")
        print("Run main.py once without --skip-fetch first, or remove the flag.")
        sys.exit(1)

    print(f"[{step_num}/{TOTAL_STEPS}] {label}... skipped (--skip-fetch), "
          f"reusing existing data/raw/")


def main():
    args = parse_args()

    run_step(1, "Preparing company list", [sys.executable, "src/prepare_companies.py"])
    run_fetch_step(args.skip_fetch)
    run_step(3, "Cleaning financials", [sys.executable, "src/clean_financials.py"])
    run_step(4, "Computing ratios", [sys.executable, "src/ratios.py"])
    run_step(5, "Computing scores (Altman Z'', Piotroski F, Beneish M)",
              [sys.executable, "src/scores.py"])
    run_step(6, "Computing red flags and risk score", [sys.executable, "src/flags.py"])

    # Step 7 runs the chart notebook instead of a plain .py file.
    # - "-m jupyter" (via sys.executable) uses this venv's own Jupyter,
    #   whatever PATH happens to point to.
    # - "--inplace" writes the executed cells and chart images back into
    #   the notebook itself, so GitHub's notebook preview shows the real
    #   output.
    # - The timeout makes a stuck cell fail loudly instead of hanging
    #   main.py forever.
    # - subprocess.run's cwd (PROJECT_ROOT) is what lets the notebook
    #   path below resolve; nbconvert then runs the notebook's own code
    #   with the *notebook's* folder as its working directory, which is
    #   a separate thing and is why the notebook's own relative paths
    #   (e.g. "../data/processed/...") still work correctly.
    run_step(7, "Executing analysis notebook (builds the chart PNGs)", [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--inplace",
        "--ExecutePreprocessor.timeout=600",
        "notebooks/02_analysis.ipynb",
    ])

    run_step(8, "Exporting Excel watchlist", [sys.executable, "src/export_excel.py"])
    run_step(9, "Building sector note (PDF + Word)", [sys.executable, "src/build_sector_note.py"])

    print()
    print("Pipeline finished. See outputs/red_flag_watchlist.xlsx and reports/sector_note.pdf")


if __name__ == "__main__":
    main()
