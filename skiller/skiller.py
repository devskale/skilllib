#!/usr/bin/env python3
"""skiller - Helper script to discover, install and manage skills for AI agents."""

import argparse
import json
import os
import sys
import yaml


def load_config():
    """Load configuration from skiller_config.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'skiller_config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {config_path} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {config_path}.")
        sys.exit(1)


def parse_frontmatter(file_path):
    """Parse YAML frontmatter from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.startswith('---\n'):
            return None
        end_pos = content.find('\n---\n', 4)
        if end_pos == -1:
            return None
        frontmatter_str = content[4:end_pos]
        return yaml.safe_load(frontmatter_str)
    except Exception:
        return None


def discover_skills(dir_path, known_subdirs):
    """Discover potential skills in the given directory."""
    if not os.path.isdir(dir_path):
        print(f"Error: Directory '{dir_path}' does not exist.")
        return

    found_any = False
    for sub in known_subdirs:
        agent_path = os.path.join(dir_path, sub)
        if os.path.exists(agent_path) and os.path.isdir(agent_path):
            print(f"Found agent directory: {sub}")
            found_any = True
            # Assume skills are subdirectories under the agent dir
            try:
                items = os.listdir(agent_path)
                skill_dirs = [item for item in items if os.path.isdir(os.path.join(agent_path, item))]
                if skill_dirs:
                    print("  Potential skills:")
                    for skill in sorted(skill_dirs):
                        skill_path = os.path.join(agent_path, skill)
                        skill_md = os.path.join(skill_path, 'SKILL.md')
                        if os.path.isfile(skill_md):
                            fm = parse_frontmatter(skill_md)
                            if fm and 'name' in fm and 'description' in fm:
                                if fm['name'] == skill:
                                    desc = fm['description'][:40]
                                    print(f"    - {skill}: {desc}")
                                else:
                                    print(f"    - {skill}: (name mismatch in frontmatter)")
                            else:
                                print(f"    - {skill}: (invalid or missing frontmatter)")
                        else:
                            print(f"    - {skill}: (no SKILL.md)")
                else:
                    print("  No skill directories found.")
            except PermissionError:
                print(f"  Permission denied accessing {agent_path}.")
        else:
            print(f"No agent directory found: {sub}")

    if not found_any:
        print("No known agent directories found in the specified directory.")


def main():
    """Main entry point for the skiller CLI."""
    config = load_config()
    known_subdirs = config.get('known_subdirs', [])

    parser = argparse.ArgumentParser(
        prog='skiller',
        description='Helper script to discover, install and manage skills for AI agents',
        epilog='Run without arguments to show help.'
    )
    parser.add_argument('--list', action='store_true', help='List all installed skills')
    parser.add_argument('--dd', nargs='?', const=os.getcwd(), metavar='DIR',
                        help='Discovery: look for known agents dirs in DIR (default: current directory) and list potential skills')

    args = parser.parse_args()

    # If no arguments provided, print help (per PRD)
    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.list:
        print("Listing installed skills... (not implemented)")
    if args.dd is not None:
        discover_skills(args.dd, known_subdirs)


if __name__ == '__main__':
    main()
