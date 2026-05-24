#!/usr/bin/env python3
"""Prepare a repository path and fetch base and feature branch refs.

Reads configuration from pr-review.json and context.json. When PullBranch is
true, clones or updates BranchFolder. When PullBranch is false, uses BranchFolder
as an existing local repository and skips clone/fetch/checkout.
Outputs metadata to {WorkFolder}/meta.json.

Usage:
    python s04_fetch_repository.py [--config PATH] [--repo-url URL]
        [--base-branch NAME] [--feature-branch NAME] [--work-dir DIR]
        [--pat TOKEN]
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    assert_standalone_git_repository, get_branch_folder, get_review_config,
    get_work_folder, get_workspace_root, print_header, print_info,
    print_success, print_warning, run_git, should_pull_branch,
    write_utf8_no_bom,
)
from _repo_case import normalize_repo


def main():
    parser = argparse.ArgumentParser(description="Clone or update repository and fetch branches.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--repo-url", help="Override Git repository URL")
    parser.add_argument("--base-branch", help="Override base branch name")
    parser.add_argument("--feature-branch", help="Override feature branch name")
    parser.add_argument("--work-dir", help="Override local clone directory")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    # Load merged configuration
    config = get_review_config(str(config_path))
    print_success(f"Loaded merged configuration from: {config_path}")

    work_folder_path = Path(get_work_folder(config, root))

    # Resolve parameters from config/overrides
    repo_url = args.repo_url
    if not repo_url:
        base_url_no_scheme = config["BaseUrl"].replace("https://", "")
        repo_url = (f"https://{config['OrganizationName']}@{base_url_no_scheme}"
                    f"/{config['OrganizationName']}/{config['ProjectName']}"
                    f"/_git/{config['RepoName']}")

    base_branch = args.base_branch or config.get("TargetBranchName")
    feature_branch = args.feature_branch or config.get("BranchName")
    pull_branch = should_pull_branch(config)
    work_dir = args.work_dir or get_branch_folder(config, root, str(work_folder_path))

    # Validate
    if not repo_url:
        print("ERROR: Repository URL not specified in config or parameters", file=sys.stderr)
        sys.exit(1)
    if not base_branch:
        print("ERROR: Base branch not specified in config or parameters", file=sys.stderr)
        sys.exit(1)
    if not feature_branch:
        print("ERROR: Feature branch not specified in config or parameters", file=sys.stderr)
        sys.exit(1)

    work_dir = str(Path(work_dir).resolve())
    meta_file = str((work_folder_path / "meta.json").resolve())

    print_header("Fetch Repository Tool")
    print_info(str(config_path), "Configuration")
    print_info(repo_url, "Repository")
    print_info(base_branch, "Base branch")
    print_info(feature_branch, "Feature branch")
    print_info(str(pull_branch), "Pull branch")
    print_info(work_dir, "Branch folder")
    if config.get("PullRequestId"):
        print_info(str(config["PullRequestId"]), "Pull Request")
    if config.get("WorkItemIds"):
        print_info(", ".join(str(i) for i in config["WorkItemIds"]), "Work Items")
    print()

    # Ensure parent directory exists
    work_parent = Path(work_dir).parent
    work_parent.mkdir(parents=True, exist_ok=True)

    review_work_root = str(work_folder_path.resolve())
    normalized_review_work_root = review_work_root.rstrip("/\\")
    normalized_work_dir = work_dir.rstrip("/\\")
    if os.name == "nt":
        work_dir_is_under_review_work_root = (
            normalized_work_dir.lower() == normalized_review_work_root.lower() or
            normalized_work_dir.lower().startswith(normalized_review_work_root.lower() + os.sep)
        )
    else:
        work_dir_is_under_review_work_root = (
            normalized_work_dir == normalized_review_work_root or
            normalized_work_dir.startswith(normalized_review_work_root + os.sep)
        )

    # Clone/update repository, or use the configured local branch folder.
    if pull_branch:
        if Path(work_dir).exists():
            try:
                assert_standalone_git_repository(work_dir, "Review workspace repository")
            except RuntimeError as exc:
                if not work_dir_is_under_review_work_root:
                    raise
                print_warning(
                    f"Existing work directory is not a standalone Git repository. "
                    f"Removing and recloning. {exc}"
                )
                shutil.rmtree(work_dir)

        if not Path(work_dir).exists():
            print("Cloning repository...")
            result = subprocess.run(["git", "clone", repo_url, work_dir],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                print(result.stderr, file=sys.stderr)
                raise RuntimeError(f"Git clone failed with exit code {result.returncode}")
        else:
            print("Repository exists; updating...")
            assert_standalone_git_repository(work_dir, "Review workspace repository")
            run_git("remote", "set-url", "origin", repo_url, cwd=work_dir)
            run_git("fetch", "--prune", "origin", cwd=work_dir)

        assert_standalone_git_repository(work_dir, "Review workspace repository")

        # Fetch base and feature branches
        print(f"Fetching base branch: origin/{base_branch}...")
        run_git("fetch", "origin", base_branch, cwd=work_dir)

        # When called from the "Code Work Item" pipeline the feature branch
        # may not yet exist on the remote (the agent will create + push it
        # later). The pr-review.json carries CreateBranchIfMissing=true in
        # that case; we fall back to checking out a fresh branch from the
        # base ref instead of failing the script.
        create_branch_if_missing = bool(config.get("CreateBranchIfMissing"))
        feature_branch_exists_remotely = True
        print(f"Fetching feature branch: origin/{feature_branch}...")
        try:
            run_git("fetch", "origin", feature_branch, cwd=work_dir)
        except RuntimeError as exc:
            if create_branch_if_missing:
                feature_branch_exists_remotely = False
                print_warning(
                    f"Feature branch '{feature_branch}' does not exist on origin yet. "
                    f"CreateBranchIfMissing=true — will branch from origin/{base_branch}."
                )
            else:
                raise

        # Disable submodule recursion
        run_git("config", "submodule.recurse", "false", cwd=work_dir, check=False)
        run_git("config", "fetch.recurseSubmodules", "false", cwd=work_dir, check=False)

        # The branch folder is a disposable review checkout that s01 deliberately
        # preserves between runs for clone-cost reasons. Sibling pipelines that
        # share this folder (e.g. Code Work Item Execution) can leave the working
        # tree dirty or even pointed at a different repo's HEAD, which would make
        # the next "git checkout -B" abort with "Your local changes ... would be
        # overwritten." Force-reset and scrub untracked files so the checkout
        # below always lands on a clean slate.
        run_git("reset", "--hard", "HEAD", cwd=work_dir, check=False)
        run_git("clean", "-fdx", cwd=work_dir, check=False)

        # Check out feature branch — from origin if it exists, otherwise from base.
        if feature_branch_exists_remotely:
            print(f"Checking out review/{feature_branch}...")
            run_git("checkout", "-B", f"review/{feature_branch}", f"origin/{feature_branch}",
                    cwd=work_dir)
        else:
            print(f"Creating new {feature_branch} from origin/{base_branch}...")
            # Use the actual feature-branch name (no "review/" prefix) so the
            # downstream agent can git-push it directly.
            run_git("checkout", "-B", feature_branch, f"origin/{base_branch}",
                    cwd=work_dir)

        # Remove nested .git entries (submodules/embedded repos)
        work_path = Path(work_dir)
        main_git = work_path / ".git"
        for nested_git in work_path.rglob(".git"):
            if nested_git != main_git:
                if nested_git.is_dir():
                    shutil.rmtree(nested_git)
                else:
                    nested_git.unlink()

        base_ref = f"origin/{base_branch}"
        # When we created the feature branch locally (not yet on origin) the
        # working copy *is* the feature ref. Using HEAD avoids a rev-parse
        # failure on the non-existent origin/<feature> ref a few lines down.
        feature_ref = (
            f"origin/{feature_branch}" if feature_branch_exists_remotely else "HEAD"
        )
    else:
        print("PullBranch is false; using existing BranchFolder without clone, fetch, or checkout.")
        assert_standalone_git_repository(work_dir, "Configured branch folder")
        base_ref = f"origin/{base_branch}"
        feature_ref = "HEAD"

    # Linux is case-sensitive; Windows-authored .sln/.slnx files often record
    # project paths in different casing than git wrote out (e.g. .sln says
    # 'Web.Core/Web.Core.csproj' but on disk it's 'Web.Core/web.core.csproj').
    # Walk the project graph and REWRITE recorded paths in the clone so they
    # match the on-disk casing exactly — every downstream command (dotnet
    # restore, dotnet build, dotnet test, npm exec ng build, etc.) resolves
    # references directly without going through invoke_build.py. The rewrites
    # live in the disposable .tmp/pr-review/branch/ checkout and never reach
    # a commit; the next s01 reset (when the branch folder is excluded) or a
    # re-clone restores pristine state.
    if os.name != "nt":
        try:
            rewrites = normalize_repo(work_dir, verbose=True)
            if rewrites:
                files_changed = sorted({r[0] for r in rewrites})
                print()
                print_success(
                    f"Case-normalised {len(rewrites)} project reference(s) "
                    f"across {len(files_changed)} file(s) in the clone."
                )
        except Exception as exc:
            print_warning(f"Case-normalization preflight failed: {exc}")

    # Get commit SHAs
    base_commit = run_git("rev-parse", base_ref, cwd=work_dir).stdout.strip()
    feature_commit = run_git("rev-parse", feature_ref, cwd=work_dir).stdout.strip()

    print()
    print_success(f"Base commit ({base_ref}): {base_commit}")
    print_success(f"Feature commit ({feature_ref}): {feature_commit}")

    # Write metadata
    meta = {
        "baseBranch": base_branch,
        "featureBranch": feature_branch,
        "baseRef": base_ref,
        "featureRef": feature_ref,
        "baseCommit": base_commit,
        "featureCommit": feature_commit,
        "pullBranch": pull_branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workDir": work_dir,
    }
    write_utf8_no_bom(meta_file, json.dumps(meta, indent=2, ensure_ascii=False))
    print()
    print_success(f"Metadata written to: {meta_file}")

    print()
    print_header("Repository Fetch Complete")


if __name__ == "__main__":
    main()
