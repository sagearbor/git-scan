Git Multi-Repo Status Scanner
A Python script to recursively scan a directory for Git repositories and display their status in a clean, compact table.

This tool is designed to replace cumbersome shell scripts that rely on parsing human-readable git status output. It uses the machine-readable --porcelain flag for reliable and consistent results.

Features
Recursive Scan: Finds all Git repositories within the specified directory and its subdirectories.

Clean Table Output: Displays results in an easy-to-read, aligned table.

"Dirty Only" Mode: A flag (-d) to hide clean repositories and only show those with pending changes.

Condensed Views: Flags (-c, -C) to truncate long repository and branch names for a more compact output.

Custom Width: Specify the exact character width for truncation.

Reliable Parsing: Uses git status --porcelain=v1 for stable, script-friendly output.

Installation and Usage
Step 1: Get the Script
Clone the repository to your local machine:

git clone [https://github.com/sagearbor/git-scan.git](https://github.com/sagearbor/git-scan.git)
cd git-scan

Step 2: Make it Executable Everywhere (Recommended)
To run the script from any directory, you should place it in a directory that is part of your system's PATH. A common practice is to have a ~/bin directory for user scripts.

Create a bin directory in your home folder if it doesn't exist:

mkdir -p ~/bin

Copy the script into your bin directory (you can also rename it for convenience):

cp git-scan.py ~/bin/git-scan

Add your ~/bin directory to your PATH safely. This command checks if ~/bin is already in your path before adding it, which prevents duplicate entries.

For Bash users (common on Linux):

echo 'if [ -d "$HOME/bin" ] && [[ ":$PATH:" != *":$HOME/bin:"* ]]; then export PATH="$HOME/bin:$PATH"; fi' >> ~/.bashrc
source ~/.bashrc

For Zsh users (common on macOS):

echo 'if [ -d "$HOME/bin" ] && [[ ":$PATH:" != *":$HOME/bin:"* ]]; then export PATH="$HOME/bin:$PATH"; fi' >> ~/.zshrc
source ~/.zshrc

Verify the installation:

which git-scan

This should output the path to your script (e.g., /home/user/bin/git-scan).

Step 3: Run the Commands
Once installed, you can run the script from anywhere.

Show help menu:

git-scan -h

Scan a specific path:

git-scan ~/projects/work

Show only repos with changes:

git-scan -d

Use the super-condensed view:

git-scan -C

Use a custom condensed view (e.g., 15 characters):

git-scan -c15

Combine flags (e.g., show dirty repos only with a 20-char width):

git-scan -d -c20

Example Output
Standard View:

Repository                                 Branch                                   Ahead Behind Staged Unstaged Untracked
------------------------------------------ ---------------------------------------- ----- ------ ------ -------- ---------
OLD_BAD/xxxOopsOralTry-Medschool_ArborTester main                                         0      0      0        1        17
word-doc-chatbot                           use_fallback_doc_with_comments               1      0      0        0         0

Super Condensed View (-C):

Repository                Branch                    Ahead Behind Staged Unstaged Untracked
------------------------- ------------------------- ----- ------ ------ -------- ---------
OLD_BAD/xxxOopsOralTry... main                          0      0      0        1        17
word-doc-chatbot          use_fallback_doc_with_...     1      0      0        0         0

