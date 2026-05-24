#!/usr/bin/env python3
"""Check (and optionally install) machine-level prerequisites for the qa-tester skill.

Replaces the PowerShell Ensure-*.ps1 scripts with a single cross-platform Python entry point.

Usage:
  python ensure_prereqs.py                  # check all
  python ensure_prereqs.py playwright       # check Playwright prereqs only
  python ensure_prereqs.py jmeter           # check JMeter prereqs only
  python ensure_prereqs.py perf             # check perf collection prereqs only
"""
import os, platform, shutil, subprocess, sys

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"

def section(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")

def ok(msg: str):   print(f"{GREEN}OK:{RESET} {msg}")
def miss(msg: str): print(f"{RED}MISSING:{RESET} {msg}")
def info(msg: str): print(msg)

def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None

def cmd_version(name: str, args: list[str] | None = None) -> str | None:
    try:
        r = subprocess.run([name] + (args or ["--version"]),
                           capture_output=True, text=True, timeout=10)
        return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 else None
    except Exception:
        return None

# ── Checks ───────────────────────────────────────────────────────────────────

def check_dotnet() -> bool:
    section(".NET SDK")
    if cmd_exists("dotnet"):
        v = cmd_version("dotnet")
        ok(f"dotnet found. {v or ''}")
        return True
    miss("dotnet not found. Install from https://dotnet.microsoft.com/download")
    return False

def check_python() -> bool:
    section("Python 3")
    v = sys.version.split()[0]
    ok(f"Python {v}")
    return True

def check_edge() -> bool:
    section("Microsoft Edge (Chromium)")
    if platform.system() != "Windows":
        info("(Edge check skipped on non-Windows — Playwright installs its own Chromium.)")
        return True
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            ok(f"Found Edge at {p}")
            return True
    miss("Microsoft Edge not found. Install from https://www.microsoft.com/edge")
    return False

def check_node() -> bool:
    section("Node.js + npm (for Playwright TS only)")
    node_ok = cmd_exists("node")
    npm_ok = cmd_exists("npm")
    if node_ok and npm_ok:
        ok(f"node {cmd_version('node') or '?'},  npm {cmd_version('npm') or '?'}")
        return True
    if not node_ok: miss("node not found.")
    if not npm_ok:  miss("npm not found.")
    info("Install from https://nodejs.org/")
    return False

def check_java() -> bool:
    section("Java runtime (for JMeter)")
    if cmd_exists("java"):
        ok(f"java found. {cmd_version('java', ['-version']) or ''}")
        return True
    miss("java not found. Install from https://learn.microsoft.com/java/openjdk/")
    return False

def check_jmeter() -> bool:
    section("Apache JMeter")
    if cmd_exists("jmeter"):
        ok("jmeter found on PATH.")
        return True
    miss("jmeter not found. Install from https://jmeter.apache.org/download_jmeter.cgi")
    return False

def check_eventpipe() -> bool:
    section("EventPipe / dotnet-trace (perf collection)")
    if cmd_exists("dotnet-trace"):
        ok(f"dotnet-trace found. {cmd_version('dotnet-trace') or ''}")
        return True
    info("dotnet-trace not found (optional — PerfCapture.cs uses in-proc EventPipe).")
    info("Install with: dotnet tool install -g dotnet-trace")
    return True  # not strictly required — in-proc EventPipe works without the CLI tool

def check_dotnet_gcdump() -> bool:
    section("dotnet-gcdump (perf soak analysis)")
    if cmd_exists("dotnet-gcdump"):
        ok(f"dotnet-gcdump found. {cmd_version('dotnet-gcdump') or ''}")
        return True
    info("dotnet-gcdump not found (optional — only needed for soak-test gcdump diffing).")
    info("Install with: dotnet tool install -g dotnet-gcdump")
    return True  # optional

# ── Suites ───────────────────────────────────────────────────────────────────

SUITES = {
    "playwright": [check_dotnet, check_python, check_edge, check_node],
    "jmeter":     [check_java, check_jmeter],
    "perf":       [check_dotnet, check_eventpipe, check_dotnet_gcdump],
    "all":        [check_dotnet, check_python, check_edge, check_node,
                   check_java, check_jmeter, check_eventpipe, check_dotnet_gcdump],
}

def main():
    suite = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    checks = SUITES.get(suite)
    if not checks:
        print(f"Unknown suite '{suite}'. Choose from: {', '.join(SUITES.keys())}")
        sys.exit(1)

    missing = []
    for check in checks:
        if not check():
            missing.append(check.__name__)

    section("Summary")
    if not missing:
        ok("All requested prerequisites are present.")
    else:
        info(f"{YELLOW}Missing: {', '.join(missing)}{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
