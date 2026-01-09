#!/usr/bin/env python3
"""
Download artifacts from a GitHub Actions workflow run.

By default, all artifact files are flattened into a single output directory.
The outer artifact.zip wrapper is automatically removed.

Usage:
    python download_artifacts.py <owner>/<repo> <run_id> [output_dir]
    python download_artifacts.py <url> [output_dir]

Examples:
    # Flatten all artifacts to single directory (default)
    python download_artifacts.py wisdom-valley/knowlify-ai 19810307537

    # Custom output directory
    python download_artifacts.py wisdom-valley/knowlify-ai 19810307537 ./artifacts

    # Keep artifacts in separate subdirectories
    python download_artifacts.py wisdom-valley/knowlify-ai 19810307537 --no-flatten

    # Using GitHub Actions URL
    python download_artifacts.py https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

import requests

# Optional imports with fallback handling
try:
    from plyer import notification as plyer_notification
except ImportError:
    plyer_notification = None

try:
    from ghtoken import get_ghtoken
except ImportError:
    get_ghtoken = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)


def send_notification(title: str, message: str) -> None:
    """
    Send a desktop notification on Ubuntu Linux.

    Tries to use plyer library first, then falls back to notify-send (Linux only).
    Silently fails with a warning if neither is available.
    """
    # Try plyer first
    if plyer_notification is not None:
        try:
            plyer_notification.notify(
                title=title,
                message=message,
                timeout=10  # 10 seconds
            )
            log.info(f"Desktop notification sent: {title}")
            return
        except Exception as e:
            log.debug(f"plyer notification failed: {e}")

    # Fall back to notify-send (Linux only)
    if platform.system() == "Linux":
        try:
            subprocess.run(
                ["notify-send", title, message],
                check=True,
                capture_output=True,
                timeout=5
            )
            log.info(f"Desktop notification sent via notify-send: {title}")
            return
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            log.warning(f"Failed to send desktop notification: {e}")
            return
    else:
        log.debug(f"Notification skipped on {platform.system()}: {title}")
        return


def wait_for_workflow_completion(
    repo: str,
    run_id: str,
    token: str,
    poll_interval: int = 60,
    timeout: int = 1800
) -> dict:
    """
    Wait for a GitHub workflow run to complete.

    Returns the completed workflow run details.
    Raises RuntimeError if timeout is exceeded.
    """
    start_time = time.time()
    elapsed: float = 0.0

    while True:
        try:
            run = get_workflow_run(repo, run_id, token)
            status = run.get("status")
            conclusion = run.get("conclusion")

            if status == "completed":
                log.info(
                    f"Workflow completed - Status: {status}, Conclusion: {conclusion}"
                )
                return run

            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            log.info(
                f"Waiting for workflow to complete (elapsed: {elapsed_str}, "
                f"status: {status})..."
            )

            if elapsed >= timeout:
                msg = f"Workflow did not complete within {timeout} seconds"
                log.error(msg)
                # Send timeout notification
                send_notification(
                    "⏱️ Workflow Timeout",
                    f"Workflow run {run_id} did not complete within {timeout // 60} minutes"
                )
                raise RuntimeError(msg)

            time.sleep(poll_interval)
        except requests.HTTPError as e:
            log.error(f"Failed to fetch workflow status: {e}")
            raise


def get_github_token() -> str:
    """Get GitHub token from environment or ghtoken package."""
    # Try environment variable first
    if token := os.environ.get("GITHUB_TOKEN"):
        return token

    # Try ghtoken package
    if get_ghtoken is not None:
        try:
            return get_ghtoken()
        except Exception:
            pass

    raise RuntimeError(
        "GitHub token not found. Set GITHUB_TOKEN environment variable or install ghtoken package."
    )


def parse_run_url(url: str) -> tuple[str, str]:
    """Parse GitHub Actions run URL to extract owner/repo and run_id."""
    # Match https://github.com/owner/repo/actions/runs/run_id
    match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/actions/runs/(\d+)",
        url
    )
    if match:
        owner, repo, run_id = match.groups()
        return f"{owner}/{repo}", run_id

    raise ValueError(
        f"Invalid GitHub Actions run URL: {url}\n"
        "Expected format: https://github.com/owner/repo/actions/runs/run_id"
    )



def download_zipfile(
    download_url: str,
    output_dir: Path,
    headers: dict[str, str],
    flatten: bool = True
) -> list[Path]:
    """
    Download and extract a zip file.

    If flatten=True, extracts artifact files to output_dir root and skips artifact.zip.
    If flatten=False, extracts to artifact-specific subdirectory.

    Returns list of extracted files (excluding artifact.zip).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp_path = Path(tmp.name)

    extracted_files = []

    try:
        log.info(f"Downloading from {download_url}...")
        response = requests.get(download_url, headers=headers, stream=True)
        response.raise_for_status()

        bytes_downloaded = 0
        with tmp_path.open("wb") as fp:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fp.write(chunk)
                    bytes_downloaded += len(chunk)

        file_size_mb = tmp_path.stat().st_size / (1024 * 1024)
        log.info(f"Downloaded {file_size_mb:.2f} MB ({bytes_downloaded} bytes)")

        # Check if zip file is empty or too small
        if tmp_path.stat().st_size == 0:
            log.warning("Downloaded file is empty!")
            return []

        log.info("Extracting...")
        try:
            with ZipFile(tmp_path) as zf:
                file_list = zf.namelist()
                log.info(f"Zip contains {len(file_list)} entries")

                if file_list:
                    log.debug(f"Zip entries: {file_list[:10]}")  # Show first 10 entries

                # Extract to temporary directory
                temp_extract_dir = Path(tempfile.mkdtemp())
                zf.extractall(temp_extract_dir)

                # If flattening, move non-artifact files to output_dir root
                if flatten:
                    for item in temp_extract_dir.rglob("*"):
                        if item.is_file():
                            # Skip artifact.zip files
                            if item.name == "artifact.zip":
                                log.info(f"Skipping artifact wrapper: {item.name}")
                                continue

                            dest = output_dir / item.name
                            # Handle name conflicts by keeping both
                            if dest.exists():
                                base = dest.stem
                                ext = dest.suffix
                                counter = 1
                                while dest.exists():
                                    dest = output_dir / f"{base}_{counter}{ext}"
                                    counter += 1

                            shutil.move(str(item), str(dest))
                            extracted_files.append(dest)
                            log.info(f"Extracted: {item.name}")
                else:
                    # Extract normally without flattening
                    zf.extractall(output_dir)
                    for item in output_dir.rglob("*"):
                        if item.is_file() and item.name != "artifact.zip":
                            extracted_files.append(item)

                # Clean up temp directory
                shutil.rmtree(temp_extract_dir, ignore_errors=True)
                log.info(f"Successfully extracted {len(extracted_files)} files")
        except Exception as e:
            log.error(f"Failed to extract zip file: {e}")
            raise

    finally:
        tmp_path.unlink(missing_ok=True)

    return extracted_files


def get_workflow_run(
    repo: str,
    run_id: str,
    token: str
) -> dict:
    """Fetch workflow run details from GitHub API."""
    api_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    log.info(f"Fetching workflow run details from {api_url}...")
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()

    return response.json()


def list_artifacts(
    repo: str,
    run_id: str,
    token: str
) -> list[tuple[str, str]]:
    """List all artifacts in a workflow run."""
    api_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    log.info(f"Fetching artifacts list from {api_url}...")
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()

    data = response.json()
    artifacts = []

    for artifact in data.get("artifacts", []):
        if not artifact.get("expired", False):
            name = artifact["name"]
            download_url = artifact["archive_download_url"]
            artifacts.append((name, download_url))
            log.info(f"  Found artifact: {name}")

    if not artifacts:
        log.warning("No non-expired artifacts found in this run")

    return artifacts


def download_artifacts(
    repo: str,
    run_id: str,
    output_dir: Optional[str] = None,
    token: Optional[str] = None,
    flatten: bool = True,
    wait: bool = True,
    poll_interval: int = 60,
    timeout: int = 3600
) -> None:
    """
    Download all artifacts from a workflow run.

    If flatten=True, all artifact files are placed in the same output directory.
    If flatten=False, each artifact gets its own subdirectory.

    If wait=True, waits for the workflow to complete before downloading.
    Only downloads artifacts if the workflow concluded with 'success'.
    """
    if token is None:
        token = get_github_token()

    if output_dir is None:
        output_dir = f"artifacts-{run_id}"

    output_path = Path(output_dir)

    # Fetch initial run details
    try:
        run = get_workflow_run(repo, run_id, token)
        log.info(
            f"Workflow run #{run['run_number']} ({run['name']}) - "
            f"Status: {run['status']}, Conclusion: {run['conclusion']}"
        )
    except requests.HTTPError as e:
        log.error(f"Failed to fetch workflow run: {e}")
        sys.exit(1)

    # Wait for workflow to complete if still running
    if wait and run.get("status") != "completed":
        log.info("Waiting for workflow to complete...")
        try:
            run = wait_for_workflow_completion(
                repo, run_id, token,
                poll_interval=poll_interval,
                timeout=timeout
            )
        except RuntimeError as e:
            log.error(str(e))
            sys.exit(1)

    # Check if workflow succeeded
    conclusion = run.get("conclusion")
    run_name = run.get("name", "Unknown")
    run_number = run.get("run_number", run_id)

    if conclusion == "success":
        log.info("✅ Workflow succeeded")
        send_notification(
            "✅ Workflow Succeeded",
            f"Run #{run_number}: {run_name}\nReady to download artifacts"
        )
    elif conclusion is not None:
        # Workflow completed but failed
        log.error(f"❌ Workflow concluded with status: {conclusion}")
        send_notification(
            "❌ Workflow Failed",
            f"Run #{run_number}: {run_name}\nConclusion: {conclusion}"
        )
        # Don't download artifacts if workflow didn't succeed
        log.info("Skipping artifact download due to unsuccessful workflow conclusion")
        sys.exit(1)
    else:
        # Conclusion is None (shouldn't happen if status is completed)
        log.error("Workflow status is unknown")
        sys.exit(1)

    # List and download artifacts
    try:
        artifacts = list_artifacts(repo, run_id, token)
    except requests.HTTPError as e:
        log.error(f"Failed to list artifacts: {e}")
        sys.exit(1)

    if not artifacts:
        log.error("No artifacts to download")
        sys.exit(1)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    total_files = 0

    for name, download_url in artifacts:
        if flatten:
            # All artifacts go to same directory
            artifact_dir = output_path
        else:
            # Each artifact in its own subdirectory
            artifact_dir = output_path / name

        # Skip if already downloaded (only for non-flattened mode)
        if not flatten and artifact_dir.exists() and any(artifact_dir.iterdir()):
            log.info(f"Artifact '{name}' already exists at {artifact_dir}; skipping")
            continue

        try:
            log.info(f"Downloading artifact '{name}'...")
            extracted_files = download_zipfile(download_url, artifact_dir, headers, flatten=flatten)
            total_files += len(extracted_files)
            log.info(f"Successfully downloaded artifact '{name}' ({len(extracted_files)} files)")
        except Exception as e:
            log.error(f"Failed to download artifact '{name}': {e}")
            sys.exit(1)

    log.info(f"All artifacts downloaded to {output_path} ({total_files} files total)")


def main():
    parser = argparse.ArgumentParser(
        description="Download artifacts from a GitHub Actions workflow run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Using owner/repo and run_id (flattened output - all files in one dir)
  python download_artifacts.py wisdom-valley/knowlify-ai 19810307537

  # With custom output directory (flattened)
  python download_artifacts.py wisdom-valley/knowlify-ai 19810307537 ./my-artifacts

  # Keep artifacts in separate subdirectories
  python download_artifacts.py wisdom-valley/knowlify-ai 19810307537 --no-flatten

  # Using full GitHub Actions URL
  python download_artifacts.py https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537

  # Using full GitHub Actions URL with custom output directory
  python download_artifacts.py https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537 ./my-artifacts
        """
    )

    parser.add_argument(
        "input",
        help="Either 'owner/repo' (requires run_id as next arg) or full GitHub Actions run URL"
    )

    parser.add_argument(
        "run_id_or_output",
        nargs="?",
        help="Either run_id (if input is owner/repo) or output directory (if input is URL)"
    )

    parser.add_argument(
        "output_dir",
        nargs="?",
        help="Output directory for artifacts (only used with owner/repo format)"
    )

    parser.add_argument(
        "--token",
        help="GitHub API token (default: read from GITHUB_TOKEN env var or ghtoken)"
    )

    parser.add_argument(
        "--no-flatten",
        action="store_true",
        help="Keep artifacts in separate subdirectories instead of flattening to one directory"
    )

    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for workflow to complete (download immediately if artifacts exist)"
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Polling interval in seconds when waiting for workflow (default: 60)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Maximum wait time in seconds (default: 1800 = 30 minutes)"
    )

    args = parser.parse_args()

    # Parse input
    repo = None
    run_id = None
    output_dir = None

    if args.input.startswith("http://") or args.input.startswith("https://"):
        # URL format: https://github.com/owner/repo/actions/runs/run_id [output_dir]
        try:
            repo, run_id = parse_run_url(args.input)
        except ValueError as e:
            log.error(str(e))
            sys.exit(1)
        # run_id_or_output becomes output_dir for URL format
        output_dir = args.run_id_or_output
    else:
        # owner/repo format: owner/repo run_id [output_dir]
        if not args.run_id_or_output:
            log.error(
                "Error: When using 'owner/repo' format, run_id is required\n"
                "Usage: python download_artifacts.py owner/repo run_id [output_dir]"
            )
            sys.exit(1)

        repo = args.input
        run_id = args.run_id_or_output
        output_dir = args.output_dir

    # Download artifacts
    try:
        flatten = not args.no_flatten
        wait = not args.no_wait
        download_artifacts(
            repo, run_id, output_dir, args.token,
            flatten=flatten,
            wait=wait,
            poll_interval=args.poll_interval,
            timeout=args.timeout
        )
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Download interrupted by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(1)
