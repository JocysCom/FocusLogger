"""
Helper module for loading merged review configuration.

This module provides functions to load and merge configuration from multiple sources:
- pr-review.json: Read-only user configuration (base settings)
- {WorkFolder}/context.json: Dynamic data fetched from Azure DevOps API

Context values take precedence over config values, allowing runtime overrides.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def get_review_config(config_path, context_path=None, verbose=False):
    """Load merged configuration from pr-review.json and {WorkFolder}/context.json.

    Args:
        config_path: Path to the base configuration file.
        context_path: Path to the dynamic context file (optional).
            If not provided, derived from config_path and WorkFolder.
        verbose: Print verbose messages.

    Returns:
        dict with merged configuration properties.
    """
    config_path = Path(config_path).resolve()

    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        if verbose:
            print(f"Loaded base configuration from: {config_path}", file=sys.stderr)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse configuration file: {exc}") from exc

    config_root = config_path.parent
    apply_config_defaults(config, config_root, verbose=verbose)

    # Determine context path if not provided
    if not context_path:
        work_folder = config.get("WorkFolder", ".tmp/pr-review")
        context_path = config_root / work_folder / "context.json"
    else:
        context_path = Path(context_path).resolve()

    # Merge context if it exists
    if context_path.is_file():
        try:
            with open(context_path, encoding="utf-8") as f:
                context = json.load(f)
            if verbose:
                print(f"Loaded dynamic context from: {context_path}", file=sys.stderr)

            # Context properties take precedence over config
            config.update(context)
            normalize_work_item_ids(config)

            if verbose:
                print("Merged context with configuration", file=sys.stderr)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARNING: Failed to load or parse context file: {exc}", file=sys.stderr)
    else:
        if verbose:
            print(f"No context file found at: {context_path}", file=sys.stderr)

    normalize_work_item_ids(config)
    return config


def apply_config_defaults(config, workspace_root, verbose=False):
    """Populate missing review configuration from Git metadata where possible."""
    config.setdefault("Type", "Azure")
    config.setdefault("AzureApiVersion", "7.1")
    config.setdefault("WorkFolder", ".tmp/pr-review")
    config.setdefault("PullBranch", False)
    config.setdefault("BranchFolder", ".")

    git_info = get_git_azure_devops_info(workspace_root)
    for key, value in git_info.items():
        if value and not config.get(key):
            config[key] = value
            if verbose:
                print(f"Derived {key} from Git: {value}", file=sys.stderr)

    normalize_work_item_ids(config)


def normalize_work_item_ids(config):
    """Normalize WorkItemIds into a de-duplicated list."""
    values = []
    work_item_ids = config.get("WorkItemIds") or []
    if not isinstance(work_item_ids, list):
        work_item_ids = [work_item_ids]

    for item in work_item_ids:
        if item not in (None, "") and item not in values:
            values.append(item)

    if values:
        config["WorkItemIds"] = values


def get_git_azure_devops_info(workspace_root):
    """Derive Azure DevOps repo details and branch names from local Git config."""
    info = {}
    root = get_git_repository_root(workspace_root) or str(Path(workspace_root).resolve())
    remote_url = run_git("remote", "get-url", "origin", cwd=root, check=False).stdout.strip()
    parsed = parse_azure_devops_remote_url(remote_url)
    if parsed:
        info.update(parsed)

    branch = run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=root, check=False).stdout.strip()
    if branch and branch != "HEAD":
        info["BranchName"] = branch

    default_ref = run_git("symbolic-ref", "--short", "refs/remotes/origin/HEAD", cwd=root,
                          check=False).stdout.strip()
    if default_ref.startswith("origin/"):
        info["TargetBranchName"] = default_ref.removeprefix("origin/")
    elif not info.get("TargetBranchName"):
        info["TargetBranchName"] = "master"

    return info


def parse_azure_devops_remote_url(remote_url):
    """Parse Azure DevOps HTTPS or SSH Git remote URL into review config values."""
    if not remote_url:
        return {}

    https_match = re.match(
        r"^https://(?:[^/@]+@)?(?P<host>dev\.azure\.com)/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/]+)$",
        remote_url,
        re.IGNORECASE,
    )
    if https_match:
        groups = https_match.groupdict()
        return {
            "BaseUrl": f"https://{groups['host']}",
            "OrganizationName": groups["org"],
            "ProjectName": groups["project"],
            "RepoName": groups["repo"],
        }

    visualstudio_match = re.match(
        r"^https://(?P<org>[^.]+)\.visualstudio\.com/(?P<project>[^/]+)/_git/(?P<repo>[^/]+)$",
        remote_url,
        re.IGNORECASE,
    )
    if visualstudio_match:
        groups = visualstudio_match.groupdict()
        return {
            "BaseUrl": "https://dev.azure.com",
            "OrganizationName": groups["org"],
            "ProjectName": groups["project"],
            "RepoName": groups["repo"],
        }

    ssh_match = re.match(
        r"^git@ssh\.dev\.azure\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+)$",
        remote_url,
        re.IGNORECASE,
    )
    if ssh_match:
        groups = ssh_match.groupdict()
        return {
            "BaseUrl": "https://dev.azure.com",
            "OrganizationName": groups["org"],
            "ProjectName": groups["project"],
            "RepoName": groups["repo"],
        }

    parsed = urlparse(remote_url)
    if parsed.netloc.endswith("dev.azure.com"):
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 4 and parts[2].lower() == "_git":
            return {
                "BaseUrl": f"{parsed.scheme}://{parsed.netloc.split('@')[-1]}",
                "OrganizationName": parts[0],
                "ProjectName": parts[1],
                "RepoName": parts[3],
            }

    return {}


def get_git_repository_root(path):
    """Return the Git repository root for a path, or None if not inside a Git repository."""
    resolved = Path(path).resolve()
    if not resolved.exists():
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=str(resolved)
        )
        if result.returncode != 0:
            return None

        git_root = result.stdout.strip()
        if not git_root:
            return None

        return str(Path(git_root).resolve())
    except OSError:
        return None


def assert_standalone_git_repository(path, description="Repository path"):
    """Ensure a path is itself the root of a standalone Git repository.

    Git commands executed from a non-repository directory can silently walk up to
    an ancestor repository. This guard prevents review scripts from modifying the
    parent workspace repository when the disposable checkout is missing or partially deleted.

    Returns:
        The git root path string.

    Raises:
        RuntimeError if the path is not a standalone Git repository root.
    """
    resolved = str(Path(path).resolve())
    if not Path(resolved).exists():
        raise RuntimeError(f"{description} does not exist: {resolved}")

    git_root = get_git_repository_root(resolved)
    if not git_root:
        raise RuntimeError(
            f"{description} is not a standalone Git repository: {resolved}\n"
            "Refusing to run Git commands here because Git would otherwise fall back "
            "to an ancestor repository if one exists."
        )

    normalized_requested = resolved.rstrip("/\\")
    normalized_root = git_root.rstrip("/\\")

    if os.name == "nt":
        match = normalized_requested.lower() == normalized_root.lower()
    else:
        match = normalized_requested == normalized_root

    if not match:
        raise RuntimeError(
            f"{description} resolves to an ancestor Git repository.\n"
            f"Requested path: {resolved}\n"
            f"Detected Git root: {git_root}\n"
            "Refusing to continue because this would modify the ancestor repository "
            "instead of the disposable review checkout."
        )

    return git_root


def get_workspace_root(start_path):
    """Locate the workspace root by walking up from a starting path until pr-review.json is found.

    Falls back to the Git repository root if pr-review.json is not found.

    Args:
        start_path: Directory to start searching from.

    Returns:
        Absolute path to the workspace root.
    """
    current = Path(start_path).resolve()
    while True:
        if (current / "pr-review.json").is_file():
            return str(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fallback: use Git repository root
    git_root = get_git_repository_root(str(Path(start_path).resolve()))
    if git_root:
        return git_root

    raise RuntimeError(
        f"Cannot determine workspace root from: {start_path}. "
        "Ensure pr-review.json exists in an ancestor directory."
    )


def get_work_folder(config, workspace_root):
    """Resolve the working folder (artifact output directory) from configuration.

    Args:
        config: Merged configuration dict (from get_review_config).
        workspace_root: Absolute path to the workspace root.

    Returns:
        Absolute path to the working folder.
    """
    relative = config.get("WorkFolder", "pr")
    return str((Path(workspace_root) / relative).resolve())


def should_pull_branch(config):
    """Return whether the PR branch should be cloned/fetched into BranchFolder."""
    value = config.get("PullBranch", True)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "off"}
    return bool(value)


def get_branch_folder(config, workspace_root, work_folder=None):
    """Resolve the local repository folder used as the PR branch checkout.

    `BranchFolder` is the current setting. `BranchPath` is accepted as a legacy
    alias for existing local configurations.
    """
    if work_folder is None:
        work_folder = get_work_folder(config, workspace_root)

    branch_folder = config.get("BranchFolder") or config.get("BranchPath")
    if not branch_folder:
        branch_folder = Path(work_folder) / "workspace" / config.get("RepoName", "repository")

    branch_folder_path = Path(branch_folder)
    if branch_folder_path.is_absolute():
        return str(branch_folder_path.resolve())

    return str((Path(workspace_root) / branch_folder_path).resolve())


def write_utf8_no_bom(path, content):
    """Write text content to a file as UTF-8 without BOM."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def read_text_file(path):
    """Read a text file, stripping BOM if present.

    Returns:
        The file content as a string.
    """
    raw = Path(path).read_bytes()
    # Strip UTF-8 BOM if present
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8")


def run_git(*args, cwd=None, check=True):
    """Run a git command and return the CompletedProcess.

    Args:
        *args: Git subcommand and arguments.
        cwd: Working directory for the git command.
        check: If True, raise on non-zero exit code.

    Returns:
        subprocess.CompletedProcess
    """
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=cwd
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"Git command failed: git {' '.join(args)}\n{stderr}")
    return result


def get_auth_headers(pat=None):
    """Build authentication headers for Azure DevOps REST API.

    Tries in order:
    1. PAT (from argument or AZDO_PAT environment variable)
    2. Azure CLI access token
    3. Empty headers (for Windows Integrated Authentication fallback)

    Args:
        pat: Personal Access Token (optional).

    Returns:
        Tuple of (headers dict, use_default_credentials bool).
    """
    import base64

    if not pat:
        pat = os.environ.get("AZDO_PAT", "")

    if pat:
        encoded = base64.b64encode(f":{pat}".encode("ascii")).decode("ascii")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }, False

    # Try Azure CLI
    print("No PAT provided. Attempting Azure CLI login...", file=sys.stderr)
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token",
             "--resource", "499b84ac-1321-427f-aa17-267ca6975798",
             "--query", "accessToken", "-o", "tsv"],
            capture_output=True, text=True
        )
        token = result.stdout.strip()
        if token and result.returncode == 0:
            encoded = base64.b64encode(f":{token}".encode("ascii")).decode("ascii")
            print("Authentication header set using Azure CLI access token.", file=sys.stderr)
            return {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json",
            }, False
    except OSError:
        pass

    print("WARNING: Azure CLI not available or login failed; "
          "falling back to Windows Integrated Authentication.", file=sys.stderr)
    return {"Content-Type": "application/json"}, True


def invoke_azdo_api(url, method="GET", headers=None, body=None, use_default_credentials=False):
    """Make an Azure DevOps REST API call.

    Args:
        url: Full API URL.
        method: HTTP method.
        headers: Request headers dict.
        body: Request body (dict or string, will be JSON-encoded if dict).
        use_default_credentials: If True, use requests auth adapters for Windows auth.

    Returns:
        Response JSON as dict, or None on failure.
    """
    import requests
    from requests_ntlm import HttpNtlmAuth  # type: ignore

    kwargs = {"headers": headers or {}}

    if body is not None:
        if isinstance(body, dict):
            kwargs["json"] = body
        else:
            kwargs["data"] = body

    if use_default_credentials:
        # On Windows, try NTLM/negotiate; on other platforms this won't work
        try:
            kwargs["auth"] = HttpNtlmAuth("", "")
        except Exception:
            pass

    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    if response.content:
        return response.json()
    return None


def print_header(title):
    """Print a formatted section header."""
    print(f"=== {title} ===")


def print_info(message, label=None):
    """Print an informational message."""
    if label:
        print(f"{label}: {message}")
    else:
        print(message)


def print_success(message):
    """Print a success message."""
    print(message)


def print_warning(message):
    """Print a warning message to stderr."""
    print(f"WARNING: {message}", file=sys.stderr)


def script_dir():
    """Return the directory containing the calling script.

    Note: This returns the directory of review_config.py itself (the scripts/ dir).
    """
    return str(Path(__file__).resolve().parent)


def skill_dir():
    """Return the skill root directory (parent of scripts/)."""
    return str(Path(__file__).resolve().parent.parent)
