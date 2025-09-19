#!/usr/bin/env python3
import os
import subprocess
import argparse

# --- Configuration for Condensed Views ---
DEFAULT_CONDENSED_WIDTH = 40
SUPER_CONDENSED_WIDTH = 25

def truncate(text, max_length):
    """Truncates text if it exceeds max_length, adding '...'."""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text

def get_git_status(repo_path):
    """
    Gathers the status of a single git repository.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain=v1', '-b'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        return None 

    output = result.stdout.strip().split('\n')
    if not output:
        return None

    # --- Parse Branch and Remote Info ---
    branch_line = output[0]
    if 'No commits yet on' in branch_line:
        branch_name = branch_line.replace('## ', '').strip()
    else:
        branch_name = branch_line.split('...')[0].replace('## ', '').strip()

    ahead, behind = 0, 0
    if '[' in branch_line and ']' in branch_line:
        remote_info = branch_line.split('[')[-1].replace(']', '')
        if 'ahead' in remote_info:
            ahead = int(remote_info.split('ahead ')[-1].split(',')[0])
        if 'behind' in remote_info:
            behind = int(remote_info.split('behind ')[-1].split(',')[0])

    # --- Parse File Status ---
    staged, unstaged, untracked = 0, 0, 0
    file_lines = output[1:]
    for line in file_lines:
        if line.startswith('??'):
            untracked += 1
        else:
            if line[0] != ' ': staged += 1
            if line[1] != ' ': unstaged += 1
    
    is_dirty = any([ahead, behind, staged, unstaged, untracked])

    return {
        "branch": branch_name, "ahead": ahead, "behind": behind,
        "staged": staged, "unstaged": unstaged, "untracked": untracked,
        "is_dirty": is_dirty,
    }

def main():
    """
    Main function to find git repos and print their status in a table.
    """
    parser = argparse.ArgumentParser(
        description="List the status of all Git repositories under a directory.",
        formatter_class=argparse.RawTextHelpFormatter # Allows for newlines in help text
    )
    parser.add_argument(
        'search_path', nargs='?', default='.',
        help='The root directory to search from. Defaults to the current directory.'
    )
    parser.add_argument(
        '-d', '--dirty-only', action='store_true',
        help='Only show repositories with changes (unpushed, unstaged, etc.).'
    )
    condensed_group = parser.add_argument_group('condensed view options')
    condensed_group.add_argument(
        '-c', '--condensed', nargs='?', type=int, const=DEFAULT_CONDENSED_WIDTH,
        metavar='WIDTH',
        help=f'Truncate long names for a compact table.\n'
             f'If used without a number, defaults to {DEFAULT_CONDENSED_WIDTH} chars.\n'
             f'You can specify a custom width, e.g., -c10 or --condensed 10.'
    )
    condensed_group.add_argument(
        '-C', '--super-condensed', dest='condensed', action='store_const',
        const=SUPER_CONDENSED_WIDTH,
        help=f'A more condensed view. Equivalent to -c{SUPER_CONDENSED_WIDTH}.'
    )
    
    args = parser.parse_args()

    root_path = os.path.abspath(args.search_path)
    if not os.path.isdir(root_path):
        print(f"Error: Directory not found at '{root_path}'")
        return

    results = []
    for dirpath, dirnames, _ in os.walk(root_path):
        if '.git' in dirnames:
            repo_path = dirpath
            status = get_git_status(repo_path)
            if status:
                results.append((os.path.relpath(repo_path, root_path), status))
            dirnames[:] = [] 

    if not results:
        print(f"No git repositories found under '{root_path}'.")
        return

    # --- Determine Column Widths ---
    is_condensed = args.condensed is not None
    if is_condensed:
        repo_col_width = args.condensed
        branch_col_width = args.condensed
    else:
        repo_col_width = len('Repository')
        branch_col_width = len('Branch')
        for path, status in results:
            display_path = path if path != '.' else os.path.basename(root_path)
            if len(display_path) > repo_col_width: repo_col_width = len(display_path)
            if len(status['branch']) > branch_col_width: branch_col_width = len(status['branch'])
        repo_col_width += 2
        branch_col_width += 2

    # --- Print Table ---
    header_template = (
        f"{{:<{repo_col_width}}} {{:<{branch_col_width}}} "
        f"{{:>5}} {{:>6}} {{:>6}} {{:>8}} {{:>9}}"
    )
    header = header_template.format(
        'Repository', 'Branch', 'Ahead', 'Behind', 'Staged', 'Unstaged', 'Untracked'
    )
    print(header)
    print('-' * len(header))

    for path, status in sorted(results):
        if args.dirty_only and not status["is_dirty"]:
            continue
        
        display_path = path if path != '.' else os.path.basename(root_path)
        branch_name = status['branch']

        if is_condensed:
            display_path = truncate(display_path, repo_col_width)
            branch_name = truncate(branch_name, branch_col_width)
        
        print(header_template.format(
            display_path,
            branch_name,
            status['ahead'],
            status['behind'],
            status['staged'],
            status['unstaged'],
            status['untracked']
        ))

if __name__ == "__main__":
    main()

