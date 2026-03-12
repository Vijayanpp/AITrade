# PIT Solutions — AI Trade Analyst
# PowerShell installer for Windows

$ClaudeDir = "$env:USERPROFILE\.claude"
$SkillsDir = "$ClaudeDir\skills"
$AgentsDir = "$ClaudeDir\agents"
$ScriptsDir = "$ClaudeDir\scripts"

$Skills = @(
    "trade-analyze",
    "trade-quick",
    "trade-scan",
    "trade-watchlist",
    "trade-report"
)

$Agents = @(
    "trade-technical",
    "trade-volume",
    "trade-pattern",
    "trade-sentiment"
)

$ScriptFiles = @(
    "data_fetcher.py",
    "indicators.py",
    "signal_engine.py",
    "pattern_scanner.py"
)

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   PIT Solutions — AI Trade Analyst Installer        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Create directories
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
New-Item -ItemType Directory -Force -Path $AgentsDir | Out-Null
New-Item -ItemType Directory -Force -Path $ScriptsDir | Out-Null

# Install main orchestrator
Write-Host "Installing main skill: trade..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$SkillsDir\trade" | Out-Null
Copy-Item "trade\SKILL.md" "$SkillsDir\trade\SKILL.md" -Force
Write-Host "  OK trade (orchestrator)" -ForegroundColor Green

# Install sub-skills
Write-Host "Installing sub-skills..." -ForegroundColor Yellow
foreach ($skill in $Skills) {
    $src = "skills\$skill\SKILL.md"
    $dest = "$SkillsDir\$skill"
    if (Test-Path $src) {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item $src "$dest\SKILL.md" -Force
        Write-Host "  OK $skill" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $src" -ForegroundColor Red
    }
}

# Install agents
Write-Host "Installing agents..." -ForegroundColor Yellow
foreach ($agent in $Agents) {
    $src = "agents\$agent.md"
    if (Test-Path $src) {
        Copy-Item $src "$AgentsDir\$agent.md" -Force
        Write-Host "  OK $agent" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $src" -ForegroundColor Red
    }
}

# Install Python scripts
Write-Host "Installing Python scripts..." -ForegroundColor Yellow
foreach ($script in $ScriptFiles) {
    $src = "scripts\$script"
    if (Test-Path $src) {
        Copy-Item $src "$ScriptsDir\$script" -Force
        Write-Host "  OK $script" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $src" -ForegroundColor Red
    }
}

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt --quiet
    Write-Host "  OK Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: pip not found. Run manually: pip install -r requirements.txt" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Available Commands:" -ForegroundColor White
Write-Host ""
Write-Host "  /trade analyze RELIANCE    — Full analysis (4 parallel agents)" -ForegroundColor Yellow
Write-Host "  /trade quick RELIANCE      — 60-second signal snapshot" -ForegroundColor Yellow
Write-Host "  /trade scan NIFTY50        — Scan entire index for setups" -ForegroundColor Yellow
Write-Host "  /trade scan watchlist      — Scan your saved watchlist" -ForegroundColor Yellow
Write-Host "  /trade watchlist add TCS   — Manage watchlist" -ForegroundColor Yellow
Write-Host "  /trade report              — End-of-day summary report" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Valid index names: NIFTY50, BANKNIFTY, NIFTY100, MIDCAP" -ForegroundColor White
Write-Host ""
Write-Host "  Disclaimer: For informational purposes only." -ForegroundColor DarkYellow
Write-Host "  Not SEBI-registered investment advice." -ForegroundColor DarkYellow
Write-Host "══════════════════════════════════════════════════════" -ForegroundColor Cyan
