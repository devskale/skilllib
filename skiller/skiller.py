#!/usr/bin/env python3
"""
skiller - Helper script to discover, install and manage skills for AI agents.

This version adds a cursor-based TUI using `questionary` when available and
falls back to simple text prompts when it's not. The TUI lets you select a
command (discovery "dd" or "list") using arrow keys, then prompts for the
command parameters. The script preserves the existing non-interactive CLI
flags: --dd and --list.

Requires:
    - pyyaml (already required)
    - questionary (optional; if missing, falls back to text prompts)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable, List, Optional

import yaml

# Try to import questionary for nice cursor-based menus. If it's not installed
# or importing fails, we'll fall back to simple input() prompts.
try:
    import questionary  # type: ignore
    from questionary import Choice  # type: ignore

    _HAVE_QUESTIONARY = True
except Exception:
    _HAVE_QUESTIONARY = False


def load_config() -> dict:
    """Load configuration from skiller_config.json located next to this file."""
    config_path = os.path.join(os.path.dirname(__file__), "skiller_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {config_path}.", file=sys.stderr)
        sys.exit(1)


def parse_frontmatter(file_path: str) -> Optional[dict]:
    """Parse YAML frontmatter (--- ... ---) from the top of a file.

    Returns the parsed YAML mapping or None if not present/invalid.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---\n"):
            return None
        end_pos = content.find("\n---\n", 4)
        if end_pos == -1:
            return None
        frontmatter_str = content[4:end_pos]
        parsed = yaml.safe_load(frontmatter_str)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception:
        return None


def discover_skills(dir_path: str, agent_subdirs: Iterable[str]) -> None:
    """Discover potential skills in the given directory.

    For each subdir in agent_subdirs, looks for that subdirectory under dir_path
    (e.g., dir_path/.opencode/skills) and lists any contained skill directories
    and whether they have valid SKILL.md frontmatter.
    """
    dir_path_exp = os.path.expanduser(dir_path)
    if not os.path.isdir(dir_path_exp):
        print(f"Error: Directory '{dir_path_exp}' does not exist.", file=sys.stderr)
        return

    found_any = False
    for sub in agent_subdirs:
        agent_path = os.path.join(dir_path_exp, sub)
        if os.path.exists(agent_path) and os.path.isdir(agent_path):
            print(f"\nFound agent directory: {agent_path}")
            found_any = True
            try:
                items = os.listdir(agent_path)
                skill_dirs = [item for item in items if os.path.isdir(os.path.join(agent_path, item))]
                if skill_dirs:
                    print("  Potential skills:")
                    for skill in sorted(skill_dirs):
                        skill_path = os.path.join(agent_path, skill)
                        skill_md = os.path.join(skill_path, "SKILL.md")
                        if os.path.isfile(skill_md):
                            fm = parse_frontmatter(skill_md)
                            if fm and "name" in fm and "description" in fm:
                                if fm["name"] == skill:
                                    desc = str(fm["description"]).replace("\n", " ")[:120]
                                    print(f"    - {skill}: {desc}")
                                else:
                                    print(f"    - {skill}: (frontmatter name mismatch)")
                            else:
                                print(f"    - {skill}: (invalid or missing frontmatter)")
                        else:
                            print(f"    - {skill}: (no SKILL.md)")
                else:
                    print("  No skill directories found.")
            except PermissionError:
                print(f"  Permission denied accessing {agent_path}.")
        else:
            # don't print an error for every expected but missing directory; print a short message
            print(f"\nNo agent directory found at: {os.path.join(dir_path_exp, sub)}")

    if not found_any:
        print("\nNo known agent directories found in the specified directory.")


def list_installed_skills_for_paths(paths: Iterable[str]) -> None:
    """List skills found under a list of directory paths.

    Each path is considered a skills root containing subdirectories for each skill.
    """
    any_found = False
    for p in paths:
        p_expanded = os.path.expanduser(p)
        if not os.path.isdir(p_expanded):
            print(f"(missing) {p_expanded}")
            continue
        try:
            items = os.listdir(p_expanded)
            skill_dirs = [item for item in items if os.path.isdir(os.path.join(p_expanded, item))]
            if skill_dirs:
                any_found = True
                print(f"\nSkills in {p_expanded}:")
                for skill in sorted(skill_dirs):
                    skill_md = os.path.join(p_expanded, skill, "SKILL.md")
                    if os.path.isfile(skill_md):
                        fm = parse_frontmatter(skill_md)
                        if fm and isinstance(fm, dict):
                            name = fm.get("name")
                            desc = fm.get("description", "")
                            desc_short = (str(desc).replace("\n", " ")[:80] + "...") if desc else "(no description)"
                            if name and name == skill:
                                print(f"  - {skill}: {desc_short}")
                            else:
                                print(f"  - {skill}: (frontmatter missing or name mismatch)")
                        else:
                            print(f"  - {skill}: (invalid frontmatter)")
                    else:
                        print(f"  - {skill}: (no SKILL.md)")
            else:
                print(f"No skills found under {p_expanded}.")
        except PermissionError:
            print(f"Permission denied accessing {p_expanded}.")
    if not any_found:
        print("\nNo skills discovered in the provided paths.")


#
# Interactive prompts (questionary-backed with fallback)
#


def _select_option(message: str, choices: List[str], default: Optional[str] = None) -> Optional[str]:
    """Select an option from choices using questionary if available, otherwise text input.

    Returns the selected choice string or None if user cancelled.
    """
    if _HAVE_QUESTIONARY:
        try:
            q_choices = [Choice(c) for c in choices]
            if default and default in choices:
                selected = questionary.select(message, choices=q_choices, default=default).ask()
            else:
                selected = questionary.select(message, choices=q_choices).ask()
            if selected is None:
                return None
            return str(selected)
        except Exception:
            # Fall back to text prompt below
            pass

    # Fallback: show numbered menu and accept a number or name
    print()
    print(message)
    for i, c in enumerate(choices, start=1):
        marker = " (default)" if default and c == default else ""
        print(f"  {i}) {c}{marker}")
    print("  q) Quit")
    while True:
        choice = input("Select an option (number or name): ").strip()
        if choice.lower() in ("q", "quit", "exit"):
            return None
        if choice == "" and default:
            return default
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        else:
            if choice in choices:
                return choice
        print("Invalid choice. Enter a number, exact option name, or 'q' to quit.")


def _text_input(message: str, default: Optional[str] = None) -> Optional[str]:
    """Prompt the user for free text. Uses questionary.text when available."""
    if _HAVE_QUESTIONARY:
        try:
            answer = questionary.text(message, default=default or "").ask()
            if answer is None:
                return None
            return str(answer).strip() or default
        except Exception:
            pass

    # fallback
    prompt = f"{message}"
    if default:
        prompt += f" [{default}]"
    prompt += ": "
    val = input(prompt).strip()
    if val == "":
        return default
    return val


def run_interactive(config: dict) -> None:
    """Run the cursor-based interactive TUI with sensible defaults."""
    agent_dirs = config.get("agent_dirs", {}) or {}
    commands = ["dd", "list", "quit"]

    cmd = _select_option("Choose a command:", commands, default="dd")
    if not cmd or cmd == "quit":
        return

    if cmd == "dd":
        # Ask for base directory (where to look for agent-specific subdirs)
        default_dir = os.getcwd()
        dir_to_use = _text_input("Discovery base directory", default=default_dir)
        if not dir_to_use:
            return
        # Ask which subdirs to search: show known agent subdirs from config if present,
        # otherwise fall back to a small default list.
        # The discovery operation used to expect a list of subdirs; we will present
        # the keys of `agent_dirs` as selectable options and allow "All known".
        subdir_choices = []
        # If config has explicit "custom_subdirs" use that by default
        custom_subs = config.get("custom_subdirs")
        if custom_subs:
            subdir_choices = list(custom_subs)
        else:
            # present agent dir keys (user-facing) as choices
            subdir_choices = list(agent_dirs.keys()) or [".opencode/skills", ".claude/skills"]

        # Let user pick one or "All"
        pick_choices = ["All"] + sorted(subdir_choices)
        pick = _select_option("Select which agent directories to search (choose 'All' to search them all):", pick_choices, default="All")
        if not pick:
            return

        if pick == "All":
            # flatten all configured agent subdir names if agent_dirs values contain explicit paths,
            # otherwise fallback to the known `subdir_choices`
            # If agent_dirs values are mappings with 'project' / 'user', we want keys used earlier.
            # For backward compatibility we will try to use 'custom_subdirs' when present.
            to_search = custom_subs if custom_subs else subdir_choices
        else:
            to_search = [pick]

        # Discover skills
        discover_skills(dir_to_use, to_search)
        return

    if cmd == "list":
        # Let user narrow which agent to list or pick All
        agents = ["All"] + sorted(agent_dirs.keys())
        choice = _select_option("Choose agent to list skills for:", agents, default="All")
        if not choice:
            return

        if choice == "All":
            # Collect paths from config (user and project) keeping order and uniqueness
            paths: List[str] = []
            seen = set()
            for a in agent_dirs.values():
                if not isinstance(a, dict):
                    continue
                for p in a.get("user", []) + a.get("project", []):
                    if p not in seen:
                        seen.add(p)
                        paths.append(p)
            if not paths:
                print("No configured agent paths to list.")
                return
            list_installed_skills_for_paths(paths)
        else:
            ad = agent_dirs.get(choice, {}) or {}
            paths = ad.get("user", []) + ad.get("project", [])
            if not paths:
                print(f"No configured paths for agent '{choice}'.")
                return
            list_installed_skills_for_paths(paths)
        return


def main() -> None:
    """Main entry point for the skiller CLI."""
    config = load_config()

    parser = argparse.ArgumentParser(
        prog="skiller",
        description="Helper script to discover, install and manage skills for AI agents",
        epilog="Run without arguments to show help.",
    )
    parser.add_argument("--list", action="store_true", help="List all installed skills")
    parser.add_argument(
        "--dd",
        nargs="?",
        const=os.getcwd(),
        metavar="DIR",
        help="Discovery: look for known agents dirs in DIR (default: current directory) and list potential skills",
    )
    parser.add_argument("--interactive", action="store_true", help="Run interactive TUI")

    args = parser.parse_args()

    # If interactive flag provided, run interactive UI
    if args.interactive:
        run_interactive(config)
        return

    # If no args provided, default to interactive with questionary when possible
    if len(sys.argv) == 1:
        # If questionary isn't available, still run interactive fallback
        run_interactive(config)
        return

    # Preserve existing CLI behavior when args are supplied
    if args.list:
        # fallback: list all paths configured
        agent_dirs = config.get("agent_dirs", {}) or {}
        paths: List[str] = []
        seen = set()
        for a in agent_dirs.values():
            if not isinstance(a, dict):
                continue
            for p in a.get("user", []) + a.get("project", []):
                if p not in seen:
                    seen.add(p)
                    paths.append(p)
        list_installed_skills_for_paths(paths)
        return

    if args.dd is not None:
        # args.dd may be None/empty due to nargs '?', but we set const to cwd so it's fine
        target = args.dd or os.getcwd()
        # If config has custom_subdirs, use them; otherwise use sensible defaults
        custom_subdirs = config.get("custom_subdirs") or [".opencode/skills", ".claude/skills"]
        discover_skills(target, custom_subdirs)
        return


if __name__ == "__main__":
    main()
