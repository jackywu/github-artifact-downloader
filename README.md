# github-artifact-downloader

Download artifacts from GitHub Actions workflow runs.

By default, all artifact files are flattened into a single output directory. The outer `artifact.zip` wrapper is automatically removed.

## Features

- ⏳ **Auto-wait for workflows**: By default, waits for the workflow to complete before downloading artifacts
- ✅ **Status validation**: Only downloads artifacts if the workflow concluded successfully
- 🔔 **Desktop notifications**: Sends desktop notifications on Linux when workflow completes (success/failure/timeout)
- 🎯 **Smart flattening**: Automatically flattens artifact directory structure (configurable)
- ⌨️ **Graceful interrupt**: Handles Ctrl+C cleanly with minimal output
- 🔐 **Flexible authentication**: Supports both `GITHUB_TOKEN` env var and `ghtoken` package

## Installation

### Option 1: Install pre-built binary

```bash
make install
```

This builds and installs the executable to `~/.local/bin/github-artifact-downloader`.

### Option 2: Build from source

```bash
make build
```

This creates an executable in the `dist/` directory. You can then copy it to your `PATH`:

```bash
cp dist/github-artifact-downloader ~/.local/bin/
```

## Usage

### Requirements

You need a GitHub token to download artifacts. Set it via:

```bash
export GITHUB_TOKEN=your_github_token
```

Or install the `ghtoken` package to automatically retrieve your token:

```bash
pip install ghtoken
```

### Basic Examples

#### Download and wait for workflow (default behavior)

```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537
```

This will:
1. Wait for the workflow to complete (checks every 60 seconds)
2. Verify the workflow succeeded
3. Download all artifacts to `./artifacts-19810307537/` (flattened)
4. Send a desktop notification when done

#### Using GitHub Actions URL

```bash
github-artifact-downloader https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537
```

#### Custom output directory

```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 ./my-artifacts
```

#### Keep artifacts in separate subdirectories

```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 --no-flatten
```

#### Don't wait for workflow (download immediately)

```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 --no-wait
```

#### Customize polling behavior

```bash
# Check every 30 seconds, timeout after 60 minutes
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 \
  --poll-interval 30 \
  --timeout 3600
```

### All Options

```
usage: github-artifact-downloader [-h] [--token TOKEN] [--no-flatten]
                                   [--no-wait] [--poll-interval POLL_INTERVAL]
                                   [--timeout TIMEOUT]
                                   input [run_id_or_output] [output_dir]

positional arguments:
  input                 Either 'owner/repo' (requires run_id as next arg) or full GitHub Actions run URL
  run_id_or_output      Either run_id (if input is owner/repo) or output directory (if input is URL)
  output_dir            Output directory for artifacts (only used with owner/repo format)

options:
  --token TOKEN         GitHub API token (default: read from GITHUB_TOKEN env var or ghtoken)
  --no-flatten          Keep artifacts in separate subdirectories instead of flattening to one directory
  --no-wait             Do not wait for workflow to complete (download immediately if artifacts exist)
  --poll-interval POLL_INTERVAL
                        Polling interval in seconds when waiting for workflow (default: 60)
  --timeout TIMEOUT     Maximum wait time in seconds (default: 1800 = 30 minutes)
```

## Desktop Notifications

The tool supports desktop notifications on Linux via:

1. **plyer** library (cross-platform support, recommended)
2. **notify-send** command (fallback, native Linux)

Notifications are sent when:
- ✅ Workflow completes successfully (before downloading)
- ❌ Workflow fails or is cancelled (skips download)
- ⏱️ Wait timeout is exceeded (no download)

If notification delivery fails, the tool continues silently with a warning message.

## Development

### Setup

```bash
uv sync --all-groups
```

This installs all dependencies including development tools (PyInstaller, etc.).

### Build

```bash
make build    # Build executable to dist/
make install  # Build and install to ~/.local/bin/
make clean    # Clean build artifacts
```

### Code quality

The project uses mypy for type checking. Configuration is in `pyproject.toml`:

```toml
[tool.mypy]
ignore_missing_imports = true
```

## Changelog

### v0.0.2
- ✨ **New**: Wait for workflow completion before downloading (enabled by default)
- ✨ **New**: Desktop notifications for workflow status (Linux)
- ✨ **New**: Status validation - only downloads on success
- ✨ **New**: Configurable polling interval and timeout
- ✨ **New**: Graceful Ctrl+C handling
- 🔧 **Improved**: Better import organization
- 🔧 **Improved**: Comprehensive plyer and dbus bundling in PyInstaller spec
- 🔧 **Improved**: Added mypy configuration for type checking
