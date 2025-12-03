#!/bin/bash
#
# Build NIXL Library and nixlbench Tool
# Clones NIXL from GitHub, builds the library with GDS enabled, and builds nixlbench
#

set -e

# Save original directory
ORIGINAL_DIR="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NIXL_REPO_URL="https://github.com/ai-dynamo/nixl.git"
NIXL_SOURCE_DIR="${NIXL_SOURCE_DIR:-$ORIGINAL_DIR/nixl}"
NIXL_INSTALL_PREFIX="${NIXL_INSTALL_PREFIX:-$ORIGINAL_DIR/install/nixl}"
NIXLBENCH_INSTALL_PREFIX="${NIXLBENCH_INSTALL_PREFIX:-$ORIGINAL_DIR/install/nixlbench}"

# Convert relative paths to absolute (if directories exist, otherwise use as-is)
if [ -d "$NIXL_SOURCE_DIR" ]; then
    NIXL_SOURCE_DIR="$(cd "$NIXL_SOURCE_DIR" && pwd)"
elif [[ "$NIXL_SOURCE_DIR" != /* ]]; then
    NIXL_SOURCE_DIR="$ORIGINAL_DIR/$NIXL_SOURCE_DIR"
fi

# Ensure install prefixes are absolute
if [[ "$NIXL_INSTALL_PREFIX" != /* ]]; then
    NIXL_INSTALL_PREFIX="$ORIGINAL_DIR/$NIXL_INSTALL_PREFIX"
fi
if [[ "$NIXLBENCH_INSTALL_PREFIX" != /* ]]; then
    NIXLBENCH_INSTALL_PREFIX="$ORIGINAL_DIR/$NIXLBENCH_INSTALL_PREFIX"
fi

# Function to print status
print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "ok" ]; then
        echo -e "${GREEN}[OK]${NC} $message"
    elif [ "$status" = "warn" ]; then
        echo -e "${YELLOW}[WARN]${NC} $message"
    elif [ "$status" = "error" ]; then
        echo -e "${RED}[ERROR]${NC} $message"
    elif [ "$status" = "info" ]; then
        echo -e "${BLUE}[INFO]${NC} $message"
    else
        echo "[ ] $message"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get version number from version string
get_version_number() {
    echo "$1" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1
}

# Function to compare version numbers (returns true if version1 >= version2)
version_ge() {
    local version1=$1
    local version2=$2
    # Use sort -V for version comparison
    # If version1 >= version2, version2 will be first when sorted (or they're equal)
    # If version1 < version2, version1 will be first when sorted
    local sorted_first=$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)
    # If sorted first equals version2, then version1 >= version2
    # OR if they're equal, either could be first, so check equality separately
    [ "$sorted_first" = "$version2" ] || [ "$version1" = "$version2" ]
}

echo "=================================="
echo "NIXL Build Script"
echo "=================================="
echo
echo "Configuration:"
echo "  NIXL Source: $NIXL_SOURCE_DIR"
echo "  NIXL Install: $NIXL_INSTALL_PREFIX"
echo "  nixlbench Install: $NIXLBENCH_INSTALL_PREFIX"
echo

# Check for required tools
echo "Checking required tools..."
echo

REQUIRED_TOOLS=("git" "meson" "ninja" "python3" "pip3" "pkg-config")
MISSING_TOOLS=()

for tool in "${REQUIRED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        version=$(${tool} --version 2>&1 | head -n1 || echo "unknown")
        print_status "ok" "$tool installed: $version"
    else
        print_status "error" "$tool NOT installed"
        MISSING_TOOLS+=("$tool")
    fi
done

echo

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo -e "${RED}Missing required tools. Please install them:${NC}"
    echo "  Ubuntu/Debian: sudo apt-get install build-essential cmake pkg-config git python3-pip"
    echo "  Fedora: sudo dnf install gcc-c++ cmake pkg-config git python3-pip"
    echo
    echo "  Python packages: pip3 install meson ninja pybind11 tomlkit"
    exit 1
fi

# Check meson version (NIXL requires >= 0.64.0)
echo "Checking meson version..."
echo

MESON_VERSION_STRING=$(meson --version 2>&1)
MESON_VERSION=$(get_version_number "$MESON_VERSION_STRING")
REQUIRED_MESON_VERSION="0.64.0"

if [ -z "$MESON_VERSION" ]; then
    print_status "warn" "Could not determine meson version"
else
    if version_ge "$MESON_VERSION" "$REQUIRED_MESON_VERSION"; then
        print_status "ok" "meson version $MESON_VERSION meets requirement (>= $REQUIRED_MESON_VERSION)"
    else
        print_status "warn" "meson version $MESON_VERSION is too old (requires >= $REQUIRED_MESON_VERSION)"
        echo -e "${YELLOW}Attempting to upgrade meson via pip...${NC}"
        if pip3 install --upgrade meson; then
            # Verify upgrade worked
            NEW_MESON_VERSION_STRING=$(meson --version 2>&1)
            NEW_MESON_VERSION=$(get_version_number "$NEW_MESON_VERSION_STRING")
            if version_ge "$NEW_MESON_VERSION" "$REQUIRED_MESON_VERSION"; then
                print_status "ok" "meson upgraded to version $NEW_MESON_VERSION"
            else
                print_status "error" "meson upgrade failed or version still too old ($NEW_MESON_VERSION)"
                echo "  Please upgrade meson manually: pip3 install --upgrade meson"
                echo "  Or install from source: https://mesonbuild.com/Getting-meson.html"
                exit 1
            fi
        else
            print_status "error" "Failed to upgrade meson"
            echo "  Please upgrade meson manually: pip3 install --upgrade meson"
            echo "  Or install from source: https://mesonbuild.com/Getting-meson.html"
            exit 1
        fi
    fi
fi

echo

# Check Python packages
echo "Checking Python packages..."
echo

PYTHON_PACKAGES=("pybind11" "tomlkit")
MISSING_PACKAGES=()

for package in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        print_status "ok" "Python package '$package' available"
    else
        print_status "warn" "Python package '$package' missing"
        MISSING_PACKAGES+=("$package")
    fi
done

echo

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}Installing missing Python packages...${NC}"
    pip3 install "${MISSING_PACKAGES[@]}"
    echo
fi

# Check for pybind11-config (needed by meson)
echo "Checking pybind11 for meson..."
echo

# Always add ~/.local/bin to PATH (where pip installs scripts)
PYTHON_USER_BIN="$HOME/.local/bin"
if [ -d "$PYTHON_USER_BIN" ]; then
    export PATH="$PYTHON_USER_BIN:$PATH"
    print_status "info" "Added $PYTHON_USER_BIN to PATH"
fi

PYBIND11_CONFIG_FOUND=false

# Check if pybind11-config is in PATH
if command_exists pybind11-config; then
    PYBIND11_VERSION=$(pybind11-config --version 2>&1 || echo "unknown")
    print_status "ok" "pybind11-config found in PATH (version $PYBIND11_VERSION)"
    PYBIND11_CONFIG_FOUND=true
else
    # Check if pybind11-config exists in common locations
    if [ -f "$PYTHON_USER_BIN/pybind11-config" ]; then
        print_status "ok" "pybind11-config found at $PYTHON_USER_BIN/pybind11-config"
        PYBIND11_CONFIG_FOUND=true
    else
        print_status "warn" "pybind11-config not found"
        echo "  Attempting to install/upgrade pybind11..."
        if pip3 install --upgrade pybind11; then
            # Check again after installation
            if command_exists pybind11-config; then
                PYBIND11_VERSION=$(pybind11-config --version 2>&1 || echo "unknown")
                print_status "ok" "pybind11-config now available (version $PYBIND11_VERSION)"
                PYBIND11_CONFIG_FOUND=true
            elif [ -f "$PYTHON_USER_BIN/pybind11-config" ]; then
                print_status "ok" "pybind11-config installed at $PYTHON_USER_BIN"
                PYBIND11_CONFIG_FOUND=true
            else
                print_status "warn" "pybind11 installed but pybind11-config not found"
                echo "  Meson may still be able to find pybind11 via pkg-config or Python"
            fi
        fi
    fi
fi

# Also check if pkg-config can find pybind11
if pkg-config --exists pybind11 2>/dev/null; then
    PYBIND11_PKG_VERSION=$(pkg-config --modversion pybind11 2>/dev/null || echo "unknown")
    print_status "ok" "pybind11 found via pkg-config (version $PYBIND11_PKG_VERSION)"
    PYBIND11_CONFIG_FOUND=true
fi

if [ "$PYBIND11_CONFIG_FOUND" = false ]; then
    print_status "warn" "pybind11 may not be found by meson"
    echo "  If build fails, try: pip3 install --upgrade pybind11"
    echo "  Or install system-wide: sudo apt-get install pybind11-dev (if available)"
fi

echo

# Check for CUDA
echo "Checking CUDA installation..."
echo

CUDA_PATH=""
NVCC_FOUND=false

# Check if CUDA_HOME is set
if [ -n "$CUDA_HOME" ]; then
    CUDA_PATH="$CUDA_HOME"
    print_status "ok" "CUDA_HOME set to: $CUDA_PATH"
elif [ -d "/usr/local/cuda" ]; then
    CUDA_PATH="/usr/local/cuda"
    print_status "ok" "Found CUDA at: $CUDA_PATH"
    # Set CUDA_HOME for the build
    export CUDA_HOME="$CUDA_PATH"
else
    print_status "warn" "CUDA directory not found at /usr/local/cuda"
    echo "  Checking other common CUDA locations..."
    # Check other common locations
    for cuda_dir in "/opt/cuda" "$HOME/cuda"; do
        if [ -d "$cuda_dir" ]; then
            CUDA_PATH="$cuda_dir"
            print_status "ok" "Found CUDA at: $CUDA_PATH"
            export CUDA_HOME="$CUDA_PATH"
            break
        fi
    done
    # Check for cuda-* directories in /usr/local
    for cuda_dir in /usr/local/cuda-*; do
        if [ -d "$cuda_dir" ]; then
            CUDA_PATH="$cuda_dir"
            print_status "ok" "Found CUDA at: $CUDA_PATH"
            export CUDA_HOME="$CUDA_PATH"
            break
        fi
    done
fi

# Check for nvcc compiler
if command_exists nvcc; then
    NVCC_VERSION=$(nvcc --version 2>&1 | grep "release" | sed 's/.*release \([0-9.]*\).*/\1/' || echo "unknown")
    print_status "ok" "nvcc found in PATH (version $NVCC_VERSION)"
    NVCC_FOUND=true
elif [ -n "$CUDA_PATH" ] && [ -f "$CUDA_PATH/bin/nvcc" ]; then
    NVCC_VERSION=$("$CUDA_PATH/bin/nvcc" --version 2>&1 | grep "release" | sed 's/.*release \([0-9.]*\).*/\1/' || echo "unknown")
    print_status "ok" "nvcc found at $CUDA_PATH/bin/nvcc (version $NVCC_VERSION)"
    # Add CUDA bin to PATH
    export PATH="$CUDA_PATH/bin:$PATH"
    NVCC_FOUND=true
else
    print_status "error" "nvcc compiler not found"
    if [ -n "$CUDA_PATH" ]; then
        echo "  CUDA directory found at: $CUDA_PATH"
        echo "  But nvcc not found at: $CUDA_PATH/bin/nvcc"
        echo "  Please ensure CUDA toolkit is properly installed"
    else
        echo "  CUDA not found. NIXL requires CUDA."
        echo "  Set CUDA_HOME or ensure CUDA is installed at /usr/local/cuda"
    fi
    exit 1
fi

# Export CUDA paths for meson
if [ -n "$CUDA_PATH" ]; then
    export CUDA_HOME="$CUDA_PATH"
    export PATH="$CUDA_PATH/bin:$PATH"
    export LD_LIBRARY_PATH="$CUDA_PATH/lib64:${LD_LIBRARY_PATH:-}"
fi

echo

# Check for UCX
echo "Checking UCX installation..."
echo

if pkg-config --exists ucx; then
    UCX_VERSION=$(pkg-config --modversion ucx)
    print_status "ok" "UCX found (version $UCX_VERSION)"
else
    print_status "warn" "UCX not found via pkg-config"
    echo "  NIXL requires UCX. See NIXL README for UCX build instructions."
fi

echo

# Clone or update NIXL repository
echo "=================================="
echo "Step 1: Cloning NIXL Repository"
echo "=================================="
echo

if [ -d "$NIXL_SOURCE_DIR" ]; then
    print_status "info" "NIXL directory exists, updating..."
    cd "$NIXL_SOURCE_DIR"
    git pull || print_status "warn" "Failed to update, continuing with existing code"
    cd "$ORIGINAL_DIR"
else
    print_status "info" "Cloning NIXL from $NIXL_REPO_URL..."
    git clone "$NIXL_REPO_URL" "$NIXL_SOURCE_DIR"
    print_status "ok" "NIXL cloned successfully"
fi

echo

# Build NIXL library
echo "=================================="
echo "Step 2: Building NIXL Library"
echo "=================================="
echo

NIXL_BUILD_DIR="$NIXL_SOURCE_DIR/build"

cd "$NIXL_SOURCE_DIR"

print_status "info" "Setting up NIXL build with meson..."
print_status "info" "Install prefix: $NIXL_INSTALL_PREFIX"

# Configure build with GDS enabled and other options
meson setup build \
    --prefix="$NIXL_INSTALL_PREFIX" \
    -Ddisable_gds_backend=false \
    -Dbuild_docs=false \
    -Dinstall_headers=true

print_status "ok" "NIXL build configured"

echo
print_status "info" "Building NIXL..."
ninja -C build

print_status "ok" "NIXL build completed"

echo
print_status "info" "Installing NIXL to $NIXL_INSTALL_PREFIX..."
ninja -C build install

print_status "ok" "NIXL installed successfully"

cd "$ORIGINAL_DIR"

echo

# Build nixlbench
echo "=================================="
echo "Step 3: Building nixlbench Tool"
echo "=================================="
echo

NIXLBENCH_SOURCE_DIR="$NIXL_SOURCE_DIR/benchmark/nixlbench"
NIXLBENCH_BUILD_DIR="$NIXLBENCH_SOURCE_DIR/build"

if [ ! -d "$NIXLBENCH_SOURCE_DIR" ]; then
    print_status "error" "nixlbench directory not found: $NIXLBENCH_SOURCE_DIR"
    exit 1
fi

cd "$NIXLBENCH_SOURCE_DIR"

print_status "info" "Setting up nixlbench build with meson..."
print_status "info" "NIXL path: $NIXL_INSTALL_PREFIX"
print_status "info" "Install prefix: $NIXLBENCH_INSTALL_PREFIX"

# Configure nixlbench build
meson setup build \
    -Dnixl_path="$NIXL_INSTALL_PREFIX" \
    --prefix="$NIXLBENCH_INSTALL_PREFIX"

print_status "ok" "nixlbench build configured"

echo
print_status "info" "Building nixlbench..."
ninja -C build

print_status "ok" "nixlbench build completed"

echo
print_status "info" "Installing nixlbench to $NIXLBENCH_INSTALL_PREFIX..."
ninja -C build install

print_status "ok" "nixlbench installed successfully"

cd "$ORIGINAL_DIR"

# Detect architecture-specific library directory
ARCH_LIB_DIR=""
if [ -d "$NIXL_INSTALL_PREFIX/lib/aarch64-linux-gnu" ]; then
    ARCH_LIB_DIR="aarch64-linux-gnu"
elif [ -d "$NIXL_INSTALL_PREFIX/lib/x86_64-linux-gnu" ]; then
    ARCH_LIB_DIR="x86_64-linux-gnu"
else
    # Try to find any architecture-specific subdirectory
    ARCH_LIB_DIR=$(find "$NIXL_INSTALL_PREFIX/lib" -maxdepth 1 -type d ! -path "$NIXL_INSTALL_PREFIX/lib" | head -n1 | xargs basename 2>/dev/null || echo "")
fi

# Determine the library path to use
if [ -n "$ARCH_LIB_DIR" ]; then
    NIXL_LIB_PATH="$NIXL_INSTALL_PREFIX/lib/$ARCH_LIB_DIR"
else
    NIXL_LIB_PATH="$NIXL_INSTALL_PREFIX/lib"
fi

echo
echo "=================================="
echo -e "${GREEN}Build Complete!${NC}"
echo "=================================="
echo
echo "Installation locations:"
echo "  NIXL library: $NIXL_INSTALL_PREFIX"
echo "  nixlbench tool: $NIXLBENCH_INSTALL_PREFIX"
echo
echo "To use nixlbench:"
echo "  export PATH=\"$NIXLBENCH_INSTALL_PREFIX/bin:\$PATH\""
echo "  export LD_LIBRARY_PATH=\"$NIXL_LIB_PATH:\$LD_LIBRARY_PATH\""
echo
echo "Example nixlbench usage:"
echo "  nixlbench --backend UCX --initiator_seg_type VRAM"
echo

