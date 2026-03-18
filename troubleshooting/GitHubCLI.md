## Problem

```
melekderman@10-248-175-189 mcdc-e-feature-PR % export HOME=/Users/$(whoami)                          
mkdir -p ~/.config/gh
gh auth login
mkdir: /Users/melekderman/.config/gh: Permission denied
```

## Solution: 

Open your terminal.

Run the command: ```ls -la ~/.config```

The output will show information like ```drwx------ 6 macuser staff ... .config```. 

The third column indicates the owner (e.g., macuser), and the fourth indicates the group (e.g., staff). 

The owner should match your current system username, which you can verify by running the command whoami. 

To do this, run:

```sudo chown -R $(whoami) ~/.config```
