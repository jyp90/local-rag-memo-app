#!/bin/bash
# Local RAG Memo — 완전 삭제 스크립트

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "⚠️  Local RAG Memo 삭제 스크립트"
echo "=================================="
echo ""
echo "삭제될 항목:"
echo "  1. 프로젝트 코드: ~/Documents/Claude/Projects/rag-memo/local-rag-memo"
echo "  2. 앱 데이터:     ~/.local-rag-memo  (문서 인덱스, 대화 히스토리)"
echo "  3. 임베딩 모델:   ~/.cache/huggingface  (~470MB)"
echo ""

# Ollama 삭제 여부 확인
echo -n "Ollama도 삭제하시겠습니까? [y/N] "
read -r REMOVE_OLLAMA

# qwen2.5:7b 삭제 여부 확인
echo -n "Ollama 모델(qwen2.5:7b)도 삭제하시겠습니까? [y/N] "
read -r REMOVE_MODEL

echo ""
echo -n "정말 삭제하시겠습니까? 되돌릴 수 없습니다. [yes/N] "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}취소되었습니다.${NC}"
    exit 0
fi

echo ""
echo "삭제 시작..."

# 앱 데이터 삭제
if [ -d "$HOME/.local-rag-memo" ]; then
    rm -rf "$HOME/.local-rag-memo"
    echo -e "${GREEN}✓ 앱 데이터 삭제 완료${NC}"
fi

# HuggingFace 모델 캐시 삭제
if [ -d "$HOME/.cache/huggingface" ]; then
    rm -rf "$HOME/.cache/huggingface"
    echo -e "${GREEN}✓ 임베딩 모델 캐시 삭제 완료${NC}"
fi

# Ollama 모델 삭제
if [ "$REMOVE_MODEL" = "y" ] || [ "$REMOVE_MODEL" = "Y" ]; then
    if command -v ollama &>/dev/null; then
        ollama rm qwen2.5:7b 2>/dev/null && echo -e "${GREEN}✓ Ollama 모델 삭제 완료${NC}" || true
    fi
fi

# Ollama 삭제
if [ "$REMOVE_OLLAMA" = "y" ] || [ "$REMOVE_OLLAMA" = "Y" ]; then
    if command -v brew &>/dev/null; then
        brew uninstall ollama 2>/dev/null && echo -e "${GREEN}✓ Ollama 삭제 완료${NC}" || true
    fi
    rm -rf "$HOME/.ollama"
    echo -e "${GREEN}✓ Ollama 데이터 삭제 완료${NC}"
fi

# 프로젝트 코드 삭제 (마지막에)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
rm -rf "$SCRIPT_DIR"
echo -e "${GREEN}✓ 프로젝트 코드 삭제 완료${NC}"

echo ""
echo -e "${GREEN}삭제 완료!${NC}"
