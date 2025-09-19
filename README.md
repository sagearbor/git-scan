# Git Multi-Repo Status Scanner

A Python script to recursively scan a directory for Git repositories and display their status in a clean, compact table.

This tool is designed to replace cumbersome shell scripts that rely on parsing human-readable `git status` output. It uses the machine-readable `--porcelain` flag for reliable and consistent results.

## Features

- **Recursive Scan:** Finds all Git repositories within the specified directory and its subdirectories.
  
- **Clean Table Output:** Displays results in an easy-to-read, aligned table.
  
- **"Dirty Only" Mode:** A flag (`-d`) to hide clean repositories and only show those with pending changes.
  
- **Condensed Views:** Flags (`-c`, `-C`) to truncate long repository and branch names for a more compact output.
  
- **Custom Width:** Specify the exact character width for truncation.
  
- **Reliable Parsing:** Uses `git status --porcelain=v1` for stable, script-friendly output.
  

## Usage

1. **Save the script:** Save the code as `git-scan.py`.
  
2. **Make it executable (Linux/macOS):**
  
  ```
  chmod +x git-scan.py
  ```
  
3. **Run the commands:**
  
  - **Show help menu:**
    
    ```
    ./git-scan.py -h
    ```
    
  - **Scan the current directory (full width):**
    
    ```
    ./git-scan.py
    ```
    
  - **Scan a specific path:**
    
    ```
    ./git-scan.py ~/projects/work
    ```
    
  - **Show only repos with changes:**
    
    ```
    ./git-scan.py -d
    ```
    
  - **Use the standard condensed view:**
    
    ```
    ./git-scan.py -c
    ```
    
  - **Use the super-condensed view:**
    
    ```
    ./git-scan.py -C
    ```
    
  - **Use a custom condensed view (e.g., 15 characters):**
    
    ```
    ./git-scan.py -c15# OR./git-scan.py --condensed 15
    ```
    
  - **Combine flags (e.g., show dirty repos only with a 20-char width):**
    
    ```
    ./git-scan.py -d -c20
    ```
    

## Example Output

**Standard View:**

```
Repository                                 Branch                                   Ahead Behind Staged Unstaged Untracked------------------------------------------ ---------------------------------------- ----- ------ ------ -------- ---------OLD_BAD/xxxOopsOralTry-Medschool_ArborTester main                                         0      0      0        1        17word-doc-chatbot                           use_fallback_doc_with_comments               1      0      0        0         0
```

**Condensed View (`-c`):**

```
Repository                               Branch                                 Ahead Behind Staged Unstaged Untracked---------------------------------------- -------------------------------------- ----- ------ ------ -------- ---------OLD_BAD/xxxOopsOralTry-Medschool_Arb...  main                                       0      0      0        1        17word-doc-chatbot                         use_fallback_doc_with_comments             1      0      0        0         0
```

**Super Condensed View (`-C`):**

```
Repository                Branch                    Ahead Behind Staged Unstaged Untracked------------------------- ------------------------- ----- ------ ------ -------- ---------OLD_BAD/xxxOopsOralTry... main                          0      0      0        1        17word-doc-chatbot          use_fallback_doc_with_...     1      0      0        0         0
```
