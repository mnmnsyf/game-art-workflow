# Install game-art-workflow as a Claude Code user skill (Windows PowerShell).
#   irm https://raw.githubusercontent.com/mnmnsyf/game-art-workflow/main/install.ps1 | iex
# Re-running updates an existing install in place.
$ErrorActionPreference = 'Stop'

$repo = 'https://github.com/mnmnsyf/game-art-workflow.git'
$root = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME '.claude\skills' }
$dest = Join-Path $root 'game-art-workflow'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required' }
New-Item -ItemType Directory -Force -Path $root | Out-Null

if (Test-Path (Join-Path $dest '.git')) {
    git -C $dest pull --ff-only
} elseif (Test-Path $dest) {
    throw "$dest exists and is not a git checkout; move it away and re-run"
} else {
    git clone --depth 1 $repo $dest
}

$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    try { python -m pip install --user --quiet -r (Join-Path $dest 'requirements.txt') }
    catch { Write-Host 'note: install Pillow yourself for the image check scripts' }
}

Write-Host "Installed to $dest"
Write-Host 'Start a new Claude Code session and ask: "Make a village house for my Godot scene"'
