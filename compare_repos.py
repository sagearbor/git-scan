import os
import re
import sys
import subprocess
import argparse
from datetime import datetime
import json

# --- DEPENDENCY CHECK ---
# The script will check if 'tabulate' is installed and provide instructions if it's not.
try:
    from tabulate import tabulate
except ImportError:
    # We only need tabulate for the terminal view, so we can proceed without it for HTML.
    pass

# --- CONFIGURE THIS ---
# Add parent directories to search for git repos.
# If this list is empty, the script will default to the current directory,
# unless a path is provided with the --dir flag.
HOME_DIR = os.path.expanduser("~")
SEARCH_DIRECTORIES = [
    os.path.join(HOME_DIR, "PROJECTS"),
]

def run_command(command, cwd, timeout=30):
    """Runs a shell command and returns its output, handling errors and timeouts."""
    try:
        result = subprocess.run(
            command, cwd=cwd, shell=True, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        # Return stderr if available, otherwise a generic error
        error_output = e.stderr.strip() if hasattr(e, 'stderr') else "Command Failed"
        return f"ERROR: {error_output}"

def find_all_repos(search_paths):
    """Recursively finds all git repositories in the given search paths."""
    found_repos = []
    print(f"Searching for repositories in: {', '.join(search_paths)}")
    for path in search_paths:
        if not os.path.isdir(path):
            print(f"Warning: Directory not found, skipping: {path}", file=sys.stderr)
            continue
        for root, dirs, _ in os.walk(path):
            if '.git' in dirs:
                repo_name = os.path.basename(root)
                found_repos.append({'name': repo_name, 'path': root})
                dirs[:] = [] # Don't go deeper into this directory
    return found_repos

def get_repo_location(repo_path):
    """Detects if a repo is from GitHub or Azure DevOps by inspecting its remote URL."""
    remote_output = run_command("git remote -v", repo_path)
    if "ERROR" in remote_output:
        return "Unknown"

    for line in remote_output.split('\n'):
        if 'origin' in line and 'fetch' in line:
            url = line.split()[1]
            if 'github.com' in url:
                return "GitHub"
            if 'dev.azure.com' in url or 'visualstudio.com' in url:
                return "Azure"
    
    # Fallback: check path for clues
    if 'devops' in repo_path.lower():
        return "Azure"
    if 'github' in repo_path.lower():
        return "GitHub"
        
    return "Other"

def get_last_commit_date(repo_path):
    """Gets the author date of the last commit."""
    command = 'git log -1 --format="%cI"' # ISO 8601 date
    output = run_command(command, repo_path)
    if "ERROR" in output or not output:
        return None
    try:
        return datetime.fromisoformat(output)
    except (ValueError, IndexError):
        return None

def get_short_relative_path(full_path, cwd):
    """Creates a truncated path relative to the current working directory."""
    try:
        relative_path = os.path.relpath(full_path, cwd)
    except ValueError:
        return full_path

    if relative_path == '.':
        return os.path.basename(full_path)

    parts = relative_path.split(os.sep)
    truncated_parts = []
    for part in parts:
        truncated_parts.append(f"{part[:6]}..." if len(part) > 6 else part)
    
    return os.path.join("./", *truncated_parts)

def get_summary_data(repo_list, cwd):
    """Gathers concise status data for a list of repositories."""
    repo_data = []
    for repo in repo_list:
        path = repo['path']
        relative_path_home = os.path.relpath(path, HOME_DIR)
        commit_date = get_last_commit_date(path)

        data = {
            'Repo': repo['name'],
            'Location': get_repo_location(path),
            'Push': 0,
            'Pull': 0,
            'Local': '',
            'Date': commit_date,
            'DateStr': commit_date.strftime('%Y-%m-%d') if commit_date else '',
            'DateTimeStr': commit_date.strftime('%Y-%m-%d %H:%M') if commit_date else '',
            'FullPath': path,
            'RelativePath': f"~/{relative_path_home}",
            'ShortRelativePath': get_short_relative_path(path, cwd)
        }

        # Check for uncommitted local changes
        status_output = run_command("git status -s", path)
        if status_output and "ERROR" not in status_output:
            data['Local'] = 'Y'

        # Check for ahead/behind commits
        branch_output = run_command("git branch -vv", path)
        if "ERROR" not in branch_output:
            for line in branch_output.split('\n'):
                if line.startswith('*'):
                    ahead_match = re.search(r'ahead (\d+)', line)
                    behind_match = re.search(r'behind (\d+)', line)
                    if ahead_match:
                        data['Push'] = int(ahead_match.group(1))
                    if behind_match:
                        data['Pull'] = int(behind_match.group(1))
                    break
        repo_data.append(data)
    return repo_data

def check_detailed_status(repo_path, repo_name):
    """The original detailed status check function."""
    print(f"--- Detailed Status: {repo_name} ({repo_path}) ---")
    run_command("git fetch --all", repo_path)
    
    status_output = run_command("git status -s", repo_path)
    if status_output and "ERROR" not in status_output:
        print(f"\n  Local Changes (Uncommitted):\n    {status_output.replace(os.linesep, f'{os.linesep}    ')}")

    branch_output = run_command("git branch -vv", repo_path)
    if "ERROR" not in branch_output:
        print(f"\n  Branch Sync Status:\n    {branch_output.replace(os.linesep, f'{os.linesep}    ')}")
    print("-" * 50 + "\n")

def parse_shortstat(stat_string):
    """Parses the output of git diff --shortstat to get insertions and deletions."""
    insertions = 0
    deletions = 0
    if "ERROR" in stat_string or not stat_string:
        return 0, 0
    
    ins_match = re.search(r'(\d+) insertion', stat_string)
    if ins_match:
        insertions = int(ins_match.group(1))
        
    del_match = re.search(r'(\d+) deletion', stat_string)
    if del_match:
        deletions = int(del_match.group(1))
        
    return insertions, deletions

def compare_repositories(path_a, path_b):
    """Compares two repos and prints a divergence report to the terminal."""
    print(f"Comparing repositories:\n  A: {path_a}\n  B: {path_b}\n")
    
    if not os.path.isdir(os.path.join(path_a, '.git')) or not os.path.isdir(os.path.join(path_b, '.git')):
        print("Error: Both paths must be valid Git repositories.", file=sys.stderr)
        return

    temp_remote_name = "_auditor_temp_remote"
    
    print("Fetching histories to find common ancestor...")
    run_command(f"git remote add {temp_remote_name} \"{os.path.abspath(path_b)}\"", path_a)
    fetch_result = run_command(f"git fetch {temp_remote_name}", path_a)
    
    if "ERROR" in fetch_result:
        print(f"Failed to fetch from temporary remote: {fetch_result}", file=sys.stderr)
        run_command(f"git remote remove {temp_remote_name}", path_a)
        return

    branch_a = run_command("git rev-parse --abbrev-ref HEAD", path_a)
    branch_b = run_command("git rev-parse --abbrev-ref HEAD", path_b)

    merge_base_cmd = f"git merge-base {branch_a} {temp_remote_name}/{branch_b}"
    merge_base_hash = run_command(merge_base_cmd, path_a)
    
    run_command(f"git remote remove {temp_remote_name}", path_a)

    if "ERROR" in merge_base_hash or not merge_base_hash:
        print("Could not find a common ancestor commit between the current branches.", file=sys.stderr)
        return

    stats_a_str = run_command(f"git diff --shortstat {merge_base_hash}", path_a)
    stats_b_str = run_command(f"git diff --shortstat {merge_base_hash}", path_b)
    
    ins_a, del_a = parse_shortstat(stats_a_str)
    ins_b, del_b = parse_shortstat(stats_b_str)
    total_a = ins_a + del_a
    total_b = ins_b + del_b

    ancestor_info = run_command(f'git show -s --format="%h %s" {merge_base_hash}', path_a)
    
    print("\n" + "=" * 80)
    print(" Repository Divergence Report")
    print("=" * 80)
    print(f"Common Ancestor: {ancestor_info}\n")
    
    table_data = [
        ["Repo A", os.path.basename(path_a), f"+{ins_a}", f"-{del_a}", total_a],
        ["Repo B", os.path.basename(path_b), f"+{ins_b}", f"-{del_b}", total_b],
    ]
    headers = ["", "Repository", "Insertions", "Deletions", "Total Lines Changed"]
    
    if 'tabulate' in sys.modules:
        print(tabulate(table_data, headers=headers, tablefmt="presto", numalign="center"))
    else:
        for row in [headers] + table_data:
            print("{:<8} {:<35} {:<12} {:<12} {:<20}".format(*row))

    if total_a > total_b:
        print(f"\nConclusion: Repo A ({os.path.basename(path_a)}) has had more changes since the split.")
    elif total_b > total_a:
        print(f"\nConclusion: Repo B ({os.path.basename(path_b)}) has had more changes since the split.")
    else:
        print("\nConclusion: Both repositories have had a similar amount of change since the split.")
    print("=" * 80 + "\n")


def generate_html_report(all_data, latest_in_group_repos, stale_in_group_repos, show_date=False, show_datetime=False):
    """Generates the main audit HTML report file."""
    html_rows = ""
    for data in sorted(all_data, key=lambda x: (x['Repo'].lower(), x['FullPath'])):
        status_class = "status-ok"
        if data['Push'] > 0 or data['Pull'] > 0:
            status_class = "status-problem"
        elif (data['Repo'], data['FullPath']) in stale_in_group_repos:
            status_class = "status-stale"
        elif data['Local'] == 'Y':
            status_class = "status-warning"
        
        is_latest = 'Y' if (data['Repo'], data['FullPath']) in latest_in_group_repos else ''
        
        date_cell = ""
        if show_datetime:
            date_cell = f"<td>{data['DateTimeStr']}</td>"
        elif show_date:
            date_cell = f"<td>{data['DateStr']}</td>"


        html_rows += f"""
        <tr class="{status_class}">
            <td>{data['Repo']}</td>
            <td>{data['Location']}</td>
            <td class="num">{data['Push'] if data['Push'] > 0 else ''}</td>
            <td class="num">{data['Pull'] if data['Pull'] > 0 else ''}</td>
            <td class="status">{data['Local']}</td>
            <td class="status">{is_latest}</td>
            {date_cell}
            <td>{data['ShortRelativePath']}</td>
        </tr>
        """
    
    date_header = ""
    if show_datetime or show_date:
        date_header = "<th>Last Commit</th>"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Git Repository Status Report</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background-color: #f8f9fa; color: #212529; }}
            .container {{ margin: 2rem; }}
            h1, h2 {{ color: #343a40; border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; }}
            .filter-container {{ margin: 1.5rem 0; }}
            #repoFilter {{ padding: 0.5rem; width: 300px; max-width: 100%; border: 1px solid #ced4da; border-radius: 0.25rem; font-size: 1rem; }}
            .legend {{ margin-bottom: 1.5rem; padding: 0.75rem; background-color: #e9ecef; border-radius: 0.25rem; font-size: 0.9rem; }}
            .legend-item {{ margin-right: 1.5rem; display: inline-flex; align-items: center; }}
            .color-box {{ width: 15px; height: 15px; display: inline-block; margin-right: 0.5rem; border: 1px solid #ccc; vertical-align: middle; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #dee2e6; }}
            thead {{ background-color: #e9ecef; }}
            th {{ font-weight: 600; cursor: pointer; user-select: none; }}
            th:hover {{ background-color: #ced4da; }}
            tbody tr:nth-child(even) {{ background-color: #f8f9fa; }}
            tbody tr:hover {{ background-color: #e2e6ea; }}
            .status-problem {{ background-color: #ffebee !important; }}
            .status-stale {{ background-color: #e3f2fd !important; }}
            .status-warning {{ background-color: #fffde7 !important; }}
            .status-ok {{ background-color: #e8f5e9 !important; }}
            .status {{ text-align: center; font-weight: bold; }}
            .num {{ text-align: center; }}
            footer {{ margin-top: 2rem; font-size: 0.8rem; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Git Repository Status Report</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <div class="filter-container">
                <input type="text" id="repoFilter" placeholder="Filter by repository name...">
            </div>
            <div class="legend">
                <strong>Legend:</strong>
                <span class="legend-item"><span class="color-box status-problem"></span> Needs Push/Pull</span>
                <span class="legend-item"><span class="color-box status-stale"></span> Stale vs. Group</span>
                <span class="legend-item"><span class="color-box status-warning"></span> Local Changes Only</span>
                <span class="legend-item"><span class="color-box status-ok"></span> In Sync</span>
            </div>
            <table id="report-table">
                <thead>
                    <tr>
                        <th>Repository</th>
                        <th>Location</th>
                        <th class="num">Push</th>
                        <th class="num">Pull</th>
                        <th class="status">Local</th>
                        <th class="status">Latest</th>
                        {date_header}
                        <th>Path</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
            <footer>Report generated by Git Auditor script. Click headers to sort.</footer>
        </div>
        <script>
            // Simple table sorting script
            document.querySelectorAll('th').forEach((headerCell, columnIndex) => {{
                headerCell.addEventListener('click', () => {{
                    const tableElement = headerCell.closest('table');
                    const tbody = tableElement.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const sortDirection = headerCell.classList.contains('sorted-asc') ? 'desc' : 'asc';
                    document.querySelectorAll('th').forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));
                    headerCell.classList.toggle(sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
                    rows.sort((a, b) => {{
                        const aValue = a.children[columnIndex].innerText;
                        const bValue = b.children[columnIndex].innerText;
                        const isNum = !isNaN(aValue) && !isNaN(bValue) && aValue.trim() !== '' && bValue.trim() !== '';
                        if (isNum) {{
                            return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
                        }} else {{
                            return sortDirection === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                        }}
                    }});
                    tbody.innerHTML = '';
                    rows.forEach(row => tbody.appendChild(row));
                }});
            }});

            // Live filter script
            const filterInput = document.getElementById('repoFilter');
            filterInput.addEventListener('keyup', () => {{
                const filterText = filterInput.value.toLowerCase();
                const tbody = document.getElementById('report-table').querySelector('tbody');
                const rows = tbody.querySelectorAll('tr');
                rows.forEach(row => {{
                    const repoNameCell = row.querySelector('td:first-child');
                    if (repoNameCell) {{
                        const repoName = repoNameCell.textContent.toLowerCase();
                        if (repoName.includes(filterText)) {{
                            row.style.display = '';
                        }} else {{
                            row.style.display = 'none';
                        }}
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """
    return html_template


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Audit Git repositories. Default is a slim table; use --html for a web report.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--compare", nargs=2, metavar=('PATH_A', 'PATH_B'),
        help="Compare two local repos and print a divergence report to the terminal before the main audit."
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Generate a sortable, color-coded HTML report file for the main audit."
    )
    parser.add_argument(
        '--dir', nargs='+',
        help="One or more directories to search. Overrides the configured SEARCH_DIRECTORIES.\n"
             "If neither is set, defaults to the current directory ('.')."
    )

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--date", action="store_true",
        help="Add a 'Last Commit' date column to the summary tables."
    )
    date_group.add_argument(
        "--datetime", action="store_true",
        help="Add a 'Last Commit' datetime column for more detail."
    )
    
    table_format_group = parser.add_argument_group('Terminal Table Formatting Options (audit mode)')
    output_group = table_format_group.add_mutually_exclusive_group()
    output_group.add_argument(
        "--detailed", action="store_true",
        help="Show a detailed, verbose report for each repository."
    )
    output_group.add_argument(
        "--full-path", action="store_true",
        help="Show summary table with full absolute paths."
    )
    output_group.add_argument(
        "--relative-path", action="store_true",
        help="Show summary table with paths relative to home (~/)."
    )
    output_group.add_argument(
        "--no-path", action="store_true",
        help="Show the slimmest summary table with no path column."
    )
    
    args = parser.parse_args()

    # --- Main Logic ---
    if args.compare:
        path_a, path_b = args.compare
        compare_repositories(path_a, path_b)
        # Continue to the main audit after printing the comparison

    # --- Default Audit Mode ---
    if args.dir:
        search_paths = args.dir
    elif SEARCH_DIRECTORIES:
        search_paths = SEARCH_DIRECTORIES
    else:
        search_paths = ['.']

    all_repos = find_all_repos(search_paths)

    if not all_repos:
        print("No Git repositories found in the specified locations.")
        sys.exit(0)

    print("Fetching repository statuses...")
    CWD = os.getcwd()
    all_data = get_summary_data(all_repos, CWD)
    
    repo_groups = {}
    for data in all_data:
        base_name = '-'.join(data['Repo'].split('-')[:4])
        if base_name not in repo_groups:
            repo_groups[base_name] = []
        repo_groups[base_name].append(data)

    latest_in_group_repos = set()
    stale_in_group_repos = set()
    for group in repo_groups.values():
        if len(group) > 1:
            latest_date_in_group = None
            latest_repo_obj = None
            for repo_data in group:
                if repo_data['Date']:
                    if latest_date_in_group is None or repo_data['Date'] > latest_date_in_group:
                        latest_date_in_group = repo_data['Date']
                        latest_repo_obj = repo_data
            if latest_repo_obj:
                latest_key = (latest_repo_obj['Repo'], latest_repo_obj['FullPath'])
                latest_in_group_repos.add(latest_key)
                for repo_data in group:
                    repo_key = (repo_data['Repo'], repo_data['FullPath'])
                    if repo_key != latest_key:
                        stale_in_group_repos.add(repo_key)

    if args.detailed:
        print("\n" + "="*60)
        print(" Detailed Status For All Found Repositories")
        print("="*60)
        for repo in sorted(all_repos, key=lambda x: x['name']):
            check_detailed_status(repo['path'], repo['name'])
    elif args.html:
        report_html = generate_html_report(all_data, latest_in_group_repos, stale_in_group_repos, args.date, args.datetime)
        report_filename = "git_report.html"
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(report_html)
        print(f"\nHTML report saved to: ./{report_filename}")
    else:
        if 'tabulate' not in sys.modules:
            print("\nError: The 'tabulate' library is required for terminal table view.", file=sys.stderr)
            print("Please install it ('pip install tabulate') or use the --html flag.", file=sys.stderr)
            sys.exit(1)
            
        table_data = []
        headers = ['Repository', 'Location', 'Push', 'Pull', 'Local', 'Latest']
        if args.datetime or args.date:
            headers.append('Last Commit')
        
        path_key = 'ShortRelativePath'
        if args.full_path:
            path_key = 'FullPath'
        elif args.relative_path:
            path_key = 'RelativePath'
        
        if not args.no_path:
            headers.append('Path')
            
        for data in sorted(all_data, key=lambda x: (x['Repo'].lower(), x['FullPath'])):
            is_latest = 'Y' if (data['Repo'], data['FullPath']) in latest_in_group_repos else ''
            
            row = [data['Repo'], data['Location'], data['Push'] if data['Push'] > 0 else '', data['Pull'] if data['Pull'] > 0 else '', data['Local'], is_latest]
            
            if args.datetime:
                row.append(data['DateTimeStr'])
            elif args.date:
                row.append(data['DateStr'])

            if not args.no_path:
                row.append(data[path_key])
            
            table_data.append(row)
            
        print("\n" + "=" * 80)
        print(" Git Repository Status Summary")
        print("=" * 80)
        print(tabulate(table_data, headers=headers, tablefmt="presto", numalign="center"))
        print("\nLegend: Push/Pull = # commits | Local Y = Uncommitted changes | Latest Y = Most recent in group")

    print("\n...Audit complete.")


