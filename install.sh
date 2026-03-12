#!/bin/bash
# PIT Solutions — AI Trade Analyst
# Install skills, agents, and scripts into Claude Code

set -e

CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"
AGENTS_DIR="$CLAUDE_DIR/agents"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"

SKILLS=(
  "trade-analyze"
  "trade-quick"
  "trade-scan"
  "trade-watchlist"
  "trade-report"
)

AGENTS=(
  "trade-technical"
  "trade-volume"
  "trade-pattern"
  "trade-sentiment"
)

SCRIPT_FILES=(
  "data_fetcher.py"
  "indicators.py"
  "signal_engine.py"
  "pattern_scanner.py"
)

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   PIT Solutions — AI Trade Analyst Installer        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Create directories
mkdir -p "$SKILLS_DIR"
mkdir -p "$AGENTS_DIR"
mkdir -p "$SCRIPTS_DIR"

# Install main orchestrator
echo "Installing main skill: trade..."
mkdir -p "$CLAUDE_DIR/skills/trade"
cp trade/SKILL.md "$CLAUDE_DIR/skills/trade/SKILL.md"

# Install sub-skills
echo "Installing sub-skills..."
for skill in "${SKILLS[@]}"; do
  if [ -d "skills/$skill" ]; then
    mkdir -p "$SKILLS_DIR/$skill"
    cp "skills/$skill/SKILL.md" "$SKILLS_DIR/$skill/SKILL.md"
    echo "  ✓ $skill"
  else
    echo "  ✗ MISSING: skills/$skill"
  fi
done

# Install agents
echo "Installing agents..."
for agent in "${AGENTS[@]}"; do
  if [ -f "agents/$agent.md" ]; then
    cp "agents/$agent.md" "$AGENTS_DIR/$agent.md"
    echo "  ✓ $agent"
  else
    echo "  ✗ MISSING: agents/$agent.md"
  fi
done

# Install Python scripts
echo "Installing Python scripts..."
for script in "${SCRIPT_FILES[@]}"; do
  if [ -f "scripts/$script" ]; then
    cp "scripts/$script" "$SCRIPTS_DIR/$script"
    echo "  ✓ $script"
  else
    echo "  ✗ MISSING: scripts/$script"
  fi
done

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
  pip3 install -r requirements.txt --quiet
  echo "  ✓ Dependencies installed"
else
  echo "  ✗ pip3 not found. Run manually: pip install -r requirements.txt"
fi

echo ""
echo "══════════════════════════════════════════════════════"
echo "  ✅ Installation complete!"
echo ""
echo "  Available Commands:"
echo ""
echo "  /trade analyze RELIANCE    — Full analysis (4 parallel agents)"
echo "  /trade quick RELIANCE      — 60-second signal snapshot"
echo "  /trade scan NIFTY50        — Scan entire index for setups"
echo "  /trade scan watchlist      — Scan your saved watchlist"
echo "  /trade watchlist add TCS   — Manage watchlist"
echo "  /trade report              — End-of-day summary report"
echo ""
echo "  Valid index names: NIFTY50, BANKNIFTY, NIFTY100, MIDCAP"
echo ""
echo "  ⚠  Disclaimer: For informational purposes only."
echo "     Not SEBI-registered investment advice."
echo "══════════════════════════════════════════════════════"
