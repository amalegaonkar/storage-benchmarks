#!/bin/bash
#
# Run All Benchmarks
# Comprehensive storage benchmark suite
#

set -e

# Configuration
RESULTS_DIR="results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================="
echo "Storage Benchmark Suite"
echo "Started: $(date)"
echo "=================================="
echo

# Create results directory
mkdir -p "$RESULTS_DIR"

# Setup check
echo -e "${YELLOW}Checking environment...${NC}"
if ! ./utils/setup_environment.sh; then
    echo "Setup check failed. Please fix issues above."
    exit 1
fi

echo
echo "=================================="
echo

# Run FIO benchmark
echo -e "${GREEN}Running FIO Benchmark...${NC}"
FIO_RESULTS="$RESULTS_DIR/fio_${TIMESTAMP}.csv"

if ./fio/fio_benchmark.py -o "$FIO_RESULTS"; then
    echo -e "${GREEN}FIO benchmark completed${NC}"
    echo "Results: $FIO_RESULTS"

    # Validate results
    echo
    echo "Validating FIO results..."
    ./utils/validate_results.py "$FIO_RESULTS"
else
    echo "FIO benchmark failed"
fi

echo
echo "=================================="
echo

# Run DD benchmark
echo -e "${GREEN}Running DD Benchmark...${NC}"
DD_RESULTS="$RESULTS_DIR/dd_${TIMESTAMP}.csv"

if ./benchmarks/dd/dd_benchmark.sh > "$DD_RESULTS" 2>&1; then
    echo -e "${GREEN}DD benchmark completed${NC}"
    echo "Results: $DD_RESULTS"
else
    echo "DD benchmark failed (may need sudo for cache clearing)"
fi

echo
echo "=================================="
echo "All Benchmarks Complete!"
echo "Finished: $(date)"
echo "=================================="
echo
echo "Results saved to:"
echo "  - $FIO_RESULTS"
echo "  - $DD_RESULTS"
echo
echo "Next steps:"
echo "  - Review results: cat $FIO_RESULTS"
echo "  - Plot results: (upload your plotting script)"
echo "  - Clean up: ./utils/cleanup.sh"
echo
