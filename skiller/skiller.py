#!/usr/bin/env python3
"""skiller - Helper script to discover, install and manage skills for AI agents."""

import argparse
import sys


def main():
    """Main entry point for the skiller CLI."""
    parser = argparse.ArgumentParser(
        prog='skiller',
        description='Helper script to discover, install and manage skills for AI agents',
        epilog='Run without arguments to show help.'
    )
    parser.add_argument('--list', action='store_true', help='List all installed skills')
    parser.add_argument('--dd', metavar='DIR', help='Discovery: look for known agents dirs in DIR and list potential skills')

    args = parser.parse_args()

    # If no arguments provided, print help (per PRD)
    if len(sys.argv) == 1:
        parser.print_help()
        return

    if args.list:
        print("Listing installed skills... (not implemented)")
    if args.dd:
        print(f"Discovering skills in '{args.dd}'... (not implemented)")


if __name__ == '__main__':
    main()
