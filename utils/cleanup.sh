#!/bin/bash
#
# Cleanup Script for Storage Benchmarks
# Removes test files and optionally clears results
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
CLEAN_RESULTS=false
CLEAN_LOGS=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --results)
            CLEAN_RESULTS=true
            shift
            ;;
        --logs)
            CLEAN_LOGS=true
            shift
            ;;
        --all)
            CLEAN_RESULTS=true
            CLEAN_LOGS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Clean up benchmark test files and optionally results/logs"
            echo
            echo "Options:"
            echo "  --results     Also remove results CSV files"
            echo "  --logs        Also remove log files"
            echo "  --all         Remove test files, results, and logs"
            echo "  --dry-run     Show what would be deleted without deleting"
            echo "  -h, --help    Show this help message"
            echo
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "Storage Benchmark Cleanup"
echo "=================================="
echo

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}"
    echo
fi

# Storage locations to clean
STORAGE_DIRS=(
    "/tmp/local-ssd"
    "/tmp/remote-pure-nfs"
)

# Clean test files
echo "Cleaning test files..."
echo

TOTAL_SIZE=0
FILE_COUNT=0

for dir in "${STORAGE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        # Find test files
        FILES=$(find "$dir" -name "test_*.bin" 2>/dev/null || true)

        if [ -n "$FILES" ]; then
            for file in $FILES; do
                size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
                size_mb=$((size / 1024 / 1024))
                TOTAL_SIZE=$((TOTAL_SIZE + size_mb))
                FILE_COUNT=$((FILE_COUNT + 1))

                if [ "$DRY_RUN" = true ]; then
                    echo "  Would delete: $file (${size_mb} MB)"
                else
                    rm -f "$file"
                    echo -e "  ${GREEN}Deleted${NC}: $file (${size_mb} MB)"
                fi
            done
        else
            echo "  No test files in $dir"
        fi
    else
        echo -e "  ${YELLOW}Directory not found${NC}: $dir"
    fi
done

echo
echo "Total: $FILE_COUNT files, ${TOTAL_SIZE} MB"
echo

# Clean results
if [ "$CLEAN_RESULTS" = true ]; then
    echo "Cleaning results..."
    echo

    if [ -d "results" ]; then
        RESULT_COUNT=$(find results -name "*.csv" 2>/dev/null | wc -l || echo 0)

        if [ $RESULT_COUNT -gt 0 ]; then
            if [ "$DRY_RUN" = true ]; then
                echo "  Would delete $RESULT_COUNT CSV files from results/"
            else
                rm -f results/*.csv
                echo -e "  ${GREEN}Deleted${NC} $RESULT_COUNT CSV files from results/"
            fi
        else
            echo "  No CSV files in results/"
        fi
    fi

    echo
fi

# Clean logs
if [ "$CLEAN_LOGS" = true ]; then
    echo "Cleaning logs..."
    echo

    if [ -d "logs" ]; then
        LOG_COUNT=$(find logs -name "*.log" 2>/dev/null | wc -l || echo 0)

        if [ $LOG_COUNT -gt 0 ]; then
            if [ "$DRY_RUN" = true ]; then
                echo "  Would delete $LOG_COUNT log files from logs/"
            else
                rm -f logs/*.log
                echo -e "  ${GREEN}Deleted${NC} $LOG_COUNT log files from logs/"
            fi
        else
            echo "  No log files in logs/"
        fi
    fi

    echo
fi

echo "=================================="
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Cleanup Preview Complete${NC}"
    echo "Run without --dry-run to delete files"
else
    echo -e "${GREEN}Cleanup Complete!${NC}"
fi
echo "=================================="
echo
