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
import shutil
import sys
from typing import Iterable, List, Optional

import yaml

# Try to import questionary for nice cursor-based menus. If it's not installed
# or importing fails, we'll fall back to curses or simple input() prompts.
try:
    import questionary  # type: ignore
    from questionary import Choice  # type: ignore

    _HAVE_QUESTIONARY = True
except Exception:
    _HAVE_QUESTIONARY = False

try:
    import curses

    _HAVE_CURSES = True
except Exception:
    _HAVE_CURSES = False


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


def _format_relative_path(path: str, base_dir: str) -> str:
    """Return path relative to base_dir with a ./ prefix when appropriate."""
    rel_path = os.path.relpath(path, start=base_dir)
    if rel_path == ".":
        return "./"
    if rel_path.startswith("../"):
        return rel_path
    if not rel_path.startswith("./"):
        rel_path = f"./{rel_path}"
    return rel_path


def list_skills_simple(dir_path: str, agent_subdirs: Iterable[str]) -> None:
    """List skills with one line per skill: dir skill description."""
    dir_path_exp = os.path.expanduser(dir_path)
    if not os.path.isdir(dir_path_exp):
        print(f"Error: Directory '{dir_path_exp}' does not exist.", file=sys.stderr)
        return

    found_any = False
    for sub in agent_subdirs:
        agent_path = os.path.join(dir_path_exp, sub)
        if not os.path.isdir(agent_path):
            continue
        found_any = True
        try:
            items = os.listdir(agent_path)
            skill_dirs = [item for item in items if os.path.isdir(os.path.join(agent_path, item))]
            for skill in sorted(skill_dirs):
                skill_path = os.path.join(agent_path, skill)
                skill_md = os.path.join(skill_path, "SKILL.md")
                description = "(no description)"
                if os.path.isfile(skill_md):
                    fm = parse_frontmatter(skill_md)
                    if fm and isinstance(fm, dict):
                        raw_desc = fm.get("description")
                        if raw_desc:
                            description = str(raw_desc).replace("\n", " ")
                rel_agent_path = _format_relative_path(agent_path, dir_path_exp)
                print(f"{rel_agent_path} {skill} {description}")
        except PermissionError:
            print(f"Permission denied accessing {agent_path}.")
    if not found_any:
        print("No known agent directories found in the specified directory.")


def _gather_skill_candidates(base_dir: str, subdirs: Iterable[str]) -> List[dict[str, str]]:
    """Return discovered skills under the given subdirectories."""
    candidates: List[dict[str, str]] = []
    for sub in subdirs:
        search_path = os.path.join(base_dir, sub)
        if not os.path.isdir(search_path):
            continue
        try:
            items = os.listdir(search_path)
        except PermissionError:
            print(f"Permission denied accessing {search_path}.")
            continue
        valid_dirs = [item for item in items if os.path.isdir(os.path.join(search_path, item))]
        for skill in sorted(valid_dirs):
            skill_path = os.path.join(search_path, skill)
            description = "(no description)"
            display_name = skill
            skill_md = os.path.join(skill_path, "SKILL.md")
            if os.path.isfile(skill_md):
                fm = parse_frontmatter(skill_md)
                if fm and isinstance(fm, dict):
                    display_name = fm.get("name") or skill
                    raw_desc = fm.get("description")
                    if raw_desc:
                        description = str(raw_desc).replace("\n", " ")
            candidates.append(
                {
                    "name": display_name,
                    "description": description,
                    "path": skill_path,
                    "rel_path": _format_relative_path(skill_path, base_dir),
                    "folder_name": os.path.basename(skill_path),
                }
            )
    return candidates


def list_installed_skills_for_paths(config: dict, paths: Iterable[str]) -> None:
    """List skills found under a list of directory paths.

    Each path is considered a skills root containing subdirectories for each skill.
    """
    # Build mapping from expanded path to label like "opencode[user]"
    path_to_label = {}
    for agent, ad in config.get("agent_dirs", {}).items():
        if not isinstance(ad, dict):
            continue
        for path_type in ["user", "project"]:
            for path in ad.get(path_type, []):
                expanded = os.path.expanduser(path)
                path_to_label[expanded] = f"{agent}[{path_type}]"

    any_found = False
    for p in paths:
        p_expanded = os.path.expanduser(p)
        if not os.path.isdir(p_expanded):
            label = path_to_label.get(p_expanded, p_expanded)
            print(f"(missing) {label}")
            continue
        try:
            items = os.listdir(p_expanded)
            skill_dirs = [item for item in items if os.path.isdir(os.path.join(p_expanded, item))]
            if skill_dirs:
                any_found = True
                label = path_to_label.get(p_expanded, p_expanded)
                print(f"\nSkills in {label}:")
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
                label = path_to_label.get(p_expanded, p_expanded)
                print(f"No skills found under {label}.")
        except PermissionError:
            label = path_to_label.get(p_expanded, p_expanded)
            print(f"Permission denied accessing {label}.")
    if not any_found:
        print("\nNo skills discovered in the provided paths.")


#
# Interactive prompts (questionary-backed with fallback)
#


_SINGLE_SELECT_HINT = "Use ↑/↓, Enter to select, q to quit"
_MULTI_SELECT_HINT = "Use ↑/↓, Space to toggle, Enter to confirm, q to quit"


def _format_prompt(message: str, hint: Optional[str] = None) -> str:
    if not hint:
        return message
    return f"{message}\n{hint}"


def _can_use_curses() -> bool:
    return _HAVE_CURSES and sys.stdin.isatty() and sys.stdout.isatty()


def _try_curses_single_select(
    message: str, choices: List[str], default: Optional[str]
) -> tuple[bool, Optional[str]]:
    if not _can_use_curses():
        return False, None
    try:
        default_index = choices.index(default) if default in choices else 0

        def _run(stdscr: "curses.window") -> Optional[str]:
            curses.curs_set(0)
            stdscr.keypad(True)
            idx = default_index
            while True:
                stdscr.clear()
                stdscr.addstr(0, 0, message)
                for i, option in enumerate(choices):
                    prefix = "> " if i == idx else "  "
                    if i == idx:
                        stdscr.addstr(i + 2, 0, f"{prefix}{option}", curses.A_REVERSE)
                    else:
                        stdscr.addstr(i + 2, 0, f"{prefix}{option}")
                stdscr.addstr(len(choices) + 3, 0, _SINGLE_SELECT_HINT)
                key = stdscr.getch()
                if key in (curses.KEY_UP, ord("k")):
                    idx = (idx - 1) % len(choices)
                elif key in (curses.KEY_DOWN, ord("j")):
                    idx = (idx + 1) % len(choices)
                elif key in (curses.KEY_ENTER, 10, 13):
                    return choices[idx]
                elif key in (27, ord("q")):
                    return None

        return True, curses.wrapper(_run)
    except Exception:
        return False, None


def _try_curses_multi_select(
    message: str, choices: List[str], default: List[str]
) -> tuple[bool, Optional[List[str]]]:
    if not _can_use_curses():
        return False, None
    try:
        default_indices = {choices.index(item) for item in default if item in choices}

        def _run(stdscr: "curses.window") -> Optional[List[str]]:
            curses.curs_set(0)
            stdscr.keypad(True)
            idx = 0
            selected = set(default_indices)
            while True:
                stdscr.clear()
                stdscr.addstr(0, 0, message)
                for i, option in enumerate(choices):
                    marker = "[x]" if i in selected else "[ ]"
                    prefix = ">" if i == idx else " "
                    line = f"{prefix} {marker} {option}"
                    if i == idx:
                        stdscr.addstr(i + 2, 0, line, curses.A_REVERSE)
                    else:
                        stdscr.addstr(i + 2, 0, line)
                stdscr.addstr(len(choices) + 3, 0, _MULTI_SELECT_HINT)
                key = stdscr.getch()
                if key in (curses.KEY_UP, ord("k")):
                    idx = (idx - 1) % len(choices)
                elif key in (curses.KEY_DOWN, ord("j")):
                    idx = (idx + 1) % len(choices)
                elif key == ord(" "):
                    if idx in selected:
                        selected.remove(idx)
                    else:
                        selected.add(idx)
                elif key in (curses.KEY_ENTER, 10, 13):
                    return [choices[i] for i in range(len(choices)) if i in selected]
                elif key in (27, ord("q")):
                    return None

        return True, curses.wrapper(_run)
    except Exception:
        return False, None


def _select_option(message: str, choices: List[str], default: Optional[str] = None) -> Optional[str]:
    """Select an option from choices using questionary if available, otherwise text input.

    Returns the selected choice string or None if user cancelled.
    """
    if _HAVE_QUESTIONARY:
        try:
            q_choices = [Choice(c) for c in choices]
            prompt = _format_prompt(message, _SINGLE_SELECT_HINT)
            if default and default in choices:
                selected = questionary.select(prompt, choices=q_choices, default=default).ask()
            else:
                selected = questionary.select(prompt, choices=q_choices).ask()
            if selected is None:
                return None
            return str(selected)
        except Exception:
            # Fall back to text prompt below
            pass

    ran_curses, selected = _try_curses_single_select(message, choices, default)
    if ran_curses:
        return selected

    # Fallback: show numbered menu and accept a number or name
    print()
    print(_format_prompt(message, _SINGLE_SELECT_HINT))
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


def _select_multiple(
    message: str, choices: List[str], default: Optional[List[str]] = None
) -> Optional[List[str]]:
    """Select multiple options using questionary when available."""
    if _HAVE_QUESTIONARY:
        try:
            q_choices = [Choice(c) for c in choices]
            prompt = _format_prompt(message, _MULTI_SELECT_HINT)
            picked = questionary.checkbox(prompt, choices=q_choices, default=default or []).ask()
            if picked is None:
                return None
            return [str(item) for item in picked]
        except Exception:
            # Fall back to text prompt below
            pass

    ran_curses, selected = _try_curses_multi_select(message, choices, default or [])
    if ran_curses:
        return selected

    print()
    print(_format_prompt(message, _MULTI_SELECT_HINT))
    for idx, choice in enumerate(choices, start=1):
        marker = " (default)" if default and choice in default else ""
        print(f"  {idx}) {choice}{marker}")
    print("  q) Quit")
    while True:
        response = input("Select options (numbers or names separated by spaces/comma): ").strip()
        if response.lower() in ("q", "quit", "exit"):
            return None
        if response == "" and default:
            return list(default)
        tokens = [token for token in response.replace(",", " ").split() if token]
        if not tokens:
            print("Enter at least one option or 'q' to quit.")
            continue
        selected: List[str] = []
        seen: set[str] = set()
        invalid = False
        for token in tokens:
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(choices):
                    value = choices[idx]
                else:
                    invalid = True
                    break
            else:
                if token in choices:
                    value = token
                else:
                    invalid = True
                    break
            if value not in seen:
                seen.add(value)
                selected.append(value)
        if invalid:
            print("One of the selections was invalid. Try again or 'q' to quit.")
            continue
        if selected:
            return selected


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


def _copy_skill_tree(source: str, destination_root: str) -> tuple[str, Optional[str]]:
    """Copy the skill directory into the destination root, avoiding overrides.

    Returns a tuple of (status, path) where status is one of: installed, exists,
    same, error.
    """
    destination_root_exp = os.path.expanduser(destination_root)
    os.makedirs(destination_root_exp, exist_ok=True)
    destination_path = os.path.join(destination_root_exp, os.path.basename(source))
    if os.path.abspath(destination_path) == os.path.abspath(source):
        return "same", destination_path
    if os.path.exists(destination_path):
        return "exists", destination_path
    try:
        shutil.copytree(source, destination_path)
    except OSError as exc:
        print(f"  Failed to install into {destination_path}: {exc}")
        return "error", destination_path
    return "installed", destination_path


def install_skill_interactive(config: dict) -> None:
    """Prompt the user to choose a discovered skill and install it."""
    base_dir = os.getcwd()
    subdirs = config.get("custom_subdirs") or [".opencode/skills", ".claude/skills"]
    candidates = _gather_skill_candidates(base_dir, subdirs)
    if not candidates:
        print("No discoverable skills found under the configured subdirectories.")
        return
    choices = []
    for candidate in candidates:
        desc = candidate["description"]
        desc_short = desc if len(desc) <= 80 else f"{desc[:77]}..."
        choices.append(f"{candidate['name']} [{candidate['rel_path']}] - {desc_short}")
    selected = _select_option("Choose a skill to install:", choices)
    if not selected:
        return
    index = choices.index(selected)
    candidate = candidates[index]

    agent_dirs = config.get("agent_dirs", {}) or {}
    if not agent_dirs:
        print("No agent configurations available to install into.")
        return
    agents = sorted(agent_dirs.keys())
    if not agents:
        print("No agents defined in configuration.")
        return
    agent_default = [agents[0]]
    selected_agents = _select_multiple("Choose agent(s) to install for:", agents, default=agent_default)
    if not selected_agents:
        return
    path_choices = ["user", "project"]
    selected_paths = _select_multiple("Choose path types to install into (user/project):", path_choices, default=["user"])
    if not selected_paths:
        return

    installed_any = False
    had_targets = False
    for agent in selected_agents:
        ad = agent_dirs.get(agent, {}) or {}
        for path_type in selected_paths:
            targets = ad.get(path_type, [])
            if not targets:
                print(f"No configured {path_type} paths for agent '{agent}'.")
                continue
            had_targets = True
            for target in targets:
                status, result_path = _copy_skill_tree(candidate["path"], target)
                if status == "installed":
                    installed_any = True
                    print(
                        f"Installed {candidate['name']} for agent '{agent}' ({path_type}) -> {result_path}"
                    )
                elif status == "exists":
                    print(
                        f"Already installed {candidate['name']} for agent '{agent}' ({path_type}) -> {result_path}"
                    )
                elif status == "same":
                    print(
                        f"Already installed {candidate['name']} for agent '{agent}' ({path_type}) -> {result_path}"
                    )
    if not had_targets:
        print("No install targets were available for the selected agents.")
    elif not installed_any:
        print("No installations were performed (targets already existed or failed).")

def run_interactive(config: dict) -> None:
    """Run the cursor-based interactive TUI with sensible defaults."""
    agent_dirs = config.get("agent_dirs", {}) or {}
    commands = ["dd", "list", "install", "quit"]

    cmd = _select_option("Choose a command:", commands, default="dd")
    if not cmd or cmd == "quit":
        return

    if cmd == "dd":
        base_dir = os.getcwd()
        subdirs = config.get("custom_subdirs") or [".opencode/skills", ".claude/skills"]
        list_skills_simple(base_dir, subdirs)
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
            list_installed_skills_for_paths(config, paths)
        else:
            ad = agent_dirs.get(choice, {}) or {}
            paths = ad.get("user", []) + ad.get("project", [])
            if not paths:
                print(f"No configured paths for agent '{choice}'.")
                return
            list_installed_skills_for_paths(config, paths)
        return

    if cmd == "install":
        install_skill_interactive(config)
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
    parser.add_argument("--install", action="store_true", help="Install a discovered skill")

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
        list_installed_skills_for_paths(config, paths)
        return

    if args.install:
        install_skill_interactive(config)
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
