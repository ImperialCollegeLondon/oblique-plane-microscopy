from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

from .config import load_config, setup_logging


def read_sync_value(sync_file: Path) -> str:
    if not sync_file.exists():
        sync_file.parent.mkdir(parents=True, exist_ok=True)
        sync_file.write_text("0", encoding="utf-8")
    return sync_file.read_text(encoding="utf-8").strip()


def write_sync_value(sync_file: Path, value: str) -> None:
    sync_file.parent.mkdir(parents=True, exist_ok=True)
    sync_file.write_text(str(value), encoding="utf-8")


def _format_command_for_log(cmd: Sequence[str]) -> str:
    """Return a readable command string without depending on a Unix shell."""
    return " ".join(f'"{part}"' if " " in part else part for part in cmd)


def run_prefind_subprocess(config_path: str | Path, nd2_file: str | Path | None = None) -> int:
    """Run one prefind pass in a fresh child Python process.

    The watcher deliberately launches the image-processing pipeline as a
    subprocess rather than importing and calling it directly. This means that
    normal Python exceptions, memory leaks, and many native-library failures in
    ND2/image-processing code do not kill the long-running watcher process.
    """
    cmd = [
        sys.executable,
        "-m",
        "dopm_nis_prefind.pipeline",
        "--config",
        str(config_path),
    ]
    if nd2_file is not None:
        cmd.extend(["--nd2", str(nd2_file)])

    logging.info("Launching prefind subprocess: %s", _format_command_for_log(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    for line in process.stdout:
        logging.info("[prefind] %s", line.rstrip())

    return_code = process.wait()
    logging.info("Prefind subprocess exited with code %d", return_code)
    return return_code


def watch_sync_file(config: dict, config_path: str | Path) -> None:
    """Poll a text file and launch a prefind subprocess when NIS writes the trigger value."""
    sync_cfg = config.get("sync", {})
    sync_file = Path(sync_cfg.get("file_path", "sync.txt"))
    trigger_value = str(sync_cfg.get("trigger_value", "1"))
    complete_value = str(sync_cfg.get("complete_value", "0"))
    error_value = str(sync_cfg.get("error_value", "E"))
    poll_seconds = float(sync_cfg.get("poll_seconds", 1.0))

    logging.info("Watching sync file: %s", sync_file)
    logging.info("Protocol: NIS writes %r; Python writes %r when complete", trigger_value, complete_value)
    logging.info("Each trigger launches a fresh child process for the one-shot prefind command")

    last_value = None
    while True:
        try:
            value = read_sync_value(sync_file)
            if value != last_value:
                logging.info("Sync value is now %r", value)
                last_value = value

            if value == trigger_value:
                logging.info("Trigger detected. Starting one-shot prefind subprocess.")
                try:
                    return_code = run_prefind_subprocess(config_path=config_path)
                    if return_code == 0:
                        write_sync_value(sync_file, complete_value)
                        logging.info("Pipeline complete. Sync value reset to %r", complete_value)
                        last_value = complete_value
                    else:
                        write_sync_value(sync_file, error_value)
                        logging.error("Pipeline failed. Sync value set to %r", error_value)
                        last_value = error_value
                except Exception:
                    logging.exception("Watcher failed while launching or supervising prefind subprocess")
                    write_sync_value(sync_file, error_value)
                    last_value = error_value

            time.sleep(poll_seconds)
        except KeyboardInterrupt:
            logging.info("Stopping sync watcher")
            return


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch a NIS-Elements sync text file and run dOPM prefind.")
    parser.add_argument("--config", default="configs/prefind_settings.yaml", help="Path to YAML config file")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    config_path = Path(args.config)
    config = load_config(config_path)
    setup_logging(config)
    watch_sync_file(config, config_path=config_path)


if __name__ == "__main__":
    main()
