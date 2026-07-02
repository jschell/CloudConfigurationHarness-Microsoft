# Git Platform CLI Tools

Installation and configuration for PR/MR CLI tools.

## Check if Installed

```bash
# GitHub
gh --version

# GitLab
glab --version

# Azure DevOps
az --version
```

## GitHub CLI (gh)

### Install

| OS | Command |
|----|---------|
| macOS | `brew install gh` |
| Ubuntu/Debian | `sudo apt install gh` |
| Fedora/RHEL | `sudo dnf install gh` |
| Arch | `sudo pacman -S github-cli` |
| Windows | `winget install GitHub.cli` |
| Windows (choco) | `choco install gh` |
| Any (conda) | `conda install -c conda-forge gh` |

Or download from: https://cli.github.com/

### Authenticate

```bash
gh auth login
# Follow prompts: GitHub.com → HTTPS → Login with browser
```

### Verify

```bash
gh auth status
```

## GitLab CLI (glab)

### Install

| OS | Command |
|----|---------|
| macOS | `brew install glab` |
| Ubuntu/Debian | `sudo apt install glab` |
| Fedora | `sudo dnf install glab` |
| Linux (snap) | `sudo snap install glab` |
| Windows | `winget install GLab.GLab` |
| Windows (choco) | `choco install glab` |
| Any (Go) | `go install gitlab.com/gitlab-org/cli/cmd/glab@latest` |

Or download from: https://gitlab.com/gitlab-org/cli

### Authenticate

```bash
# For gitlab.com
glab auth login

# For self-hosted GitLab
glab auth login --hostname gitlab.mycompany.com
```

### Verify

```bash
glab auth status
```

## Azure DevOps CLI (az repos)

### Install

Azure CLI with DevOps extension:

| OS | Command |
|----|---------|
| macOS | `brew install azure-cli` |
| Ubuntu/Debian | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| Fedora/RHEL | `sudo dnf install azure-cli` |
| Windows | `winget install Microsoft.AzureCLI` |
| Windows (choco) | `choco install azure-cli` |
| Any (pip) | `pip install azure-cli` |

Then add DevOps extension:
```bash
az extension add --name azure-devops
```

Or download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

### Authenticate

```bash
# Interactive login
az login

# Set default organization
az devops configure --defaults organization=https://dev.azure.com/myorg
```

### Verify

```bash
az devops project list
```

## Bitbucket

No official CLI. Options:

1. **Web UI** - Create PR at bitbucket.org
2. **Unofficial CLI** - `pip install bitbucket-cli`
3. **API** - Use curl with app passwords

## Quick Setup Scripts

### macOS/Linux (Bash)

```bash
#!/bin/bash
# setup-git-cli.sh - Install CLI for detected platform

remote=$(git remote get-url origin 2>/dev/null)

case "$remote" in
  *github.com*)
    echo "Installing GitHub CLI..."
    brew install gh 2>/dev/null || sudo apt install gh 2>/dev/null || sudo dnf install gh
    gh auth login
    ;;
  *gitlab.com*)
    echo "Installing GitLab CLI..."
    brew install glab 2>/dev/null || sudo apt install glab 2>/dev/null || sudo dnf install glab
    glab auth login
    ;;
  *dev.azure.com*)
    echo "Installing Azure CLI..."
    brew install azure-cli 2>/dev/null || curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    az extension add --name azure-devops
    az login
    ;;
  *)
    echo "Unknown platform. Use web UI for PR creation."
    ;;
esac
```

### Windows (PowerShell)

```powershell
# setup-git-cli.ps1 - Install CLI for detected platform

$remote = git remote get-url origin 2>$null

if ($remote -match "github.com") {
    Write-Host "Installing GitHub CLI..."
    winget install GitHub.cli
    gh auth login
}
elseif ($remote -match "gitlab.com") {
    Write-Host "Installing GitLab CLI..."
    winget install GLab.GLab
    glab auth login
}
elseif ($remote -match "dev.azure.com") {
    Write-Host "Installing Azure CLI..."
    winget install Microsoft.AzureCLI
    az extension add --name azure-devops
    az login
}
else {
    Write-Host "Unknown platform. Use web UI for PR creation."
}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "gh: command not found" | Install gh CLI (see above) |
| "not logged in" | Run `gh auth login` / `glab auth login` |
| "permission denied" | Check token scopes include repo/PR access |
| Self-hosted GitLab | Use `glab auth login --hostname <host>` |
| Corporate proxy | Set `HTTPS_PROXY` env var |
