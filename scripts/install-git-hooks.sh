#!/bin/bash
# Git Hook Installation Script
# Installs post-commit hook for automatic RAG ingestion
#
# Usage: ./install-git-hooks.sh [repo_path]

set -e

REPO_PATH="${1:-.}"
HOOK_DIR="$REPO_PATH/.git/hooks"
HOOK_SCRIPT="post-commit"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔧 安装 Git Hooks...${NC}"

# Check if .git exists
if [ ! -d "$REPO_PATH/.git" ]; then
    echo -e "${RED}❌ 不是有效的 Git 仓库: $REPO_PATH${NC}"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOK_DIR"

# Determine the path to the hook script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_HOOK="$SCRIPT_DIR/git-hook-post-commit.sh"

if [ ! -f "$SOURCE_HOOK" ]; then
    echo -e "${RED}❌ 找不到源 hook 脚本: $SOURCE_HOOK${NC}"
    exit 1
fi

# Copy hook script
TARGET_HOOK="$HOOK_DIR/$HOOK_SCRIPT"
cp "$SOURCE_HOOK" "$TARGET_HOOK"
chmod +x "$TARGET_HOOK"

echo -e "${GREEN}✅ Git Hook 已安装:${NC}"
echo "   位置: $TARGET_HOOK"
echo ""
echo -e "${YELLOW}📝 配置步骤:${NC}"
echo "1. 设置 API 地址和虚拟密钥:"
echo "   export TEAM_AI_PLATFORM_URL=http://localhost:8000"
echo "   export TEAM_AI_PLATFORM_KEY=your-virtual-key"
echo ""
echo "2. 或者创建配置文件:"
echo "   mkdir -p ~/.team"
echo "   cat > ~/.team/config.json << 'EOF'"
echo "   {"
echo "     \"virtual_key\": \"your-virtual-key\","
echo "     \"api_url\": \"http://localhost:8000\""
echo "   }"
echo "   EOF"
echo ""
echo "3. 禁用 hooks (如果需要):"
echo "   touch ~/.team/disable-git-hooks"
echo ""
echo -e "${GREEN}✅ 安装完成!${NC}"
echo "   下一次提交时 hook 将自动触发"
