#!/bin/bash

# ================================================================
# Mermaid Diagram to PNG Converter
# ================================================================
# Converts all .mmd files in docs/diagrams/ to PNG images
# Requirements: @mermaid-js/mermaid-cli (installed via npm)
# Usage: ./scripts/generate-diagrams.sh
# ================================================================

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Mermaid Diagram Generator${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check if mmdc is installed
if ! command -v mmdc &> /dev/null
then
    echo -e "${RED}Error: mermaid-cli (mmdc) is not installed${NC}"
    echo "Install it with: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

# Define paths
DIAGRAM_DIR="docs/diagrams"
OUTPUT_DIR="docs/images"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Convert each .mmd file to PNG
echo -e "${BLUE}Converting diagrams...${NC}"
echo ""

for mmd_file in "$DIAGRAM_DIR"/*.mmd; do
    if [ -f "$mmd_file" ]; then
        filename=$(basename "$mmd_file" .mmd)
        output_file="$OUTPUT_DIR/${filename}.png"

        echo -e "  ${GREEN}✓${NC} Converting ${filename}.mmd → ${filename}.png"

        mmdc -i "$mmd_file" \
             -o "$output_file" \
             -b transparent \
             -w 1920 \
             -H 1080 \
             --quiet
    fi
done

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Conversion Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Generated images are in: $OUTPUT_DIR/"
echo ""
echo "Files created:"
ls -lh "$OUTPUT_DIR"/*.png
echo ""
echo -e "${BLUE}Tip:${NC} Use these PNG files in your presentation slides"
