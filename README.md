# github-artifact-downloader

Download artifacts from GitHub Actions workflow runs.

By default, all artifact files are flattened into a single output directory. The outer `artifact.zip` wrapper is automatically removed.

## Installation

### Build from source

```bash
make build
```

This creates an executable in the `dist/` directory.

### Install to PATH

```bash
sudo cp dist/github-artifact-downloader /usr/local/bin/
```

Or for user-local installation:

```bash
cp dist/github-artifact-downloader ~/.local/bin/
```

## Usage

### Requirements

You need a GitHub token to download artifacts. Set it via:

```bash
export GITHUB_TOKEN=your_github_token
```

Or install the `ghtoken` package to automatically retrieve your token.

### Basic Usage

#### Using owner/repo and run_id (flattened output)

```bash
github-artifact-downloader <owner>/<repo> <run_id>
```

Example:
```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537
```

#### With custom output directory (flattened)

```bash
github-artifact-downloader <owner>/<repo> <run_id> ./output_dir
```

Example:
```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 ./my-artifacts
```

#### Keep artifacts in separate subdirectories

```bash
github-artifact-downloader <owner>/<repo> <run_id> --no-flatten
```

Example:
```bash
github-artifact-downloader wisdom-valley/knowlify-ai 19810307537 --no-flatten
```

#### Using full GitHub Actions URL

```bash
github-artifact-downloader <url> [output_dir]
```

Example:
```bash
github-artifact-downloader https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537
```

Or with custom output directory:
```bash
github-artifact-downloader https://github.com/wisdom-valley/knowlify-ai/actions/runs/19810307537 ./my-artifacts
```

### Options

- `--no-flatten`: Keep each artifact in its own subdirectory instead of flattening all files to one directory
- `--token`: Specify GitHub API token directly (default: read from `GITHUB_TOKEN` env var or `ghtoken`)

## Build

```bash
make build
```

This will:
- Use `uv` to run PyInstaller
- Generate the `github-artifact-downloader` executable in the `dist/` directory

### Clean build artifacts

```bash
make clean
```

This removes the `build/`, `dist/`, and `.spec.bak` files.
