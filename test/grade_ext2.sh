#!/bin/bash

# Comprehensive EXT2 Testing Script
# This simulates what a grader might run

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TOTAL_TESTS=0
PASSED_TESTS=0

echo "========================================="
echo "     EXT2 Filesystem Grading Script"
echo "========================================="
echo ""

# Function to run a test and track results
run_test() {
    local test_name="$1"
    local command="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Running: $test_name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

# Clean and compile
echo "Step 1: Compilation"
echo "-------------------"
run_test "Clean build" "make clean"
run_test "Compile" "make"
run_test "Executable exists" "test -f ext2-create"
echo ""

# Create filesystem
echo "Step 2: Filesystem Creation"
echo "---------------------------"
run_test "Create filesystem" "./ext2-create"
run_test "Image exists" "test -f cs111-base.img"
run_test "Image size is 1MiB" "test \$(stat -f%z cs111-base.img 2>/dev/null || stat -c%s cs111-base.img 2>/dev/null) -eq 1048576"
echo ""

# Basic structure tests
echo "Step 3: Basic Structure Tests"
echo "------------------------------"

# Check for magic number
run_test "Magic number present" "hexdump -s 1080 -n 2 -e '2/1 \"%02x\"' cs111-base.img | grep -q '53ef'"

# Check superblock values using hexdump
run_test "Inode count = 128" "hexdump -s 1024 -n 4 -e '1/4 \"%u\"' cs111-base.img | grep -q '^128$'"
run_test "Block count = 1024" "hexdump -s 1028 -n 4 -e '1/4 \"%u\"' cs111-base.img | grep -q '^1024$'"
run_test "Free blocks = 1000" "hexdump -s 1036 -n 4 -e '1/4 \"%u\"' cs111-base.img | grep -q '^1000$'"
run_test "Free inodes = 115" "hexdump -s 1040 -n 4 -e '1/4 \"%u\"' cs111-base.img | grep -q '^115$'"
echo ""

# File content test
echo "Step 4: File Content Tests"
echo "--------------------------"
run_test "Hello world content" "dd if=cs111-base.img bs=1024 skip=23 count=1 2>/dev/null | head -c 12 | grep -q 'Hello world'"
run_test "Content has newline" "dd if=cs111-base.img bs=1024 skip=23 count=1 2>/dev/null | od -c | grep -q '\\\\n'"
echo ""

# Bitmap tests
echo "Step 5: Bitmap Tests"
echo "--------------------"
run_test "Block bitmap first byte" "hexdump -s 3072 -n 1 -e '1/1 \"%02x\"' cs111-base.img | grep -q 'ff'"
run_test "Inode bitmap first byte" "hexdump -s 4096 -n 1 -e '1/1 \"%02x\"' cs111-base.img | grep -q 'ff'"
run_test "Inode bitmap second byte" "hexdump -s 4097 -n 1 -e '1/1 \"%02x\"' cs111-base.img | grep -q '1f'"
echo ""

# Python unit tests
echo "Step 6: Python Unit Tests"
echo "-------------------------"
if command -v python3 &> /dev/null; then
    run_test "Original unit tests" "python3 -m unittest test_lab5 2>/dev/null"
    
    if [ -f "test_ext2_comprehensive.py" ]; then
        run_test "Comprehensive tests" "python3 test_ext2_comprehensive.py 2>/dev/null"
    fi
    
    if [ -f "test_edge_cases.py" ]; then
        run_test "Edge case tests" "python3 test_edge_cases.py 2>/dev/null"
    fi
else
    echo -e "${YELLOW}Python3 not found - skipping Python tests${NC}"
fi
echo ""

# fsck test (if available)
echo "Step 7: Filesystem Check"
echo "------------------------"
if command -v e2fsck &> /dev/null; then
    run_test "e2fsck reports clean" "e2fsck -f -n cs111-base.img 2>&1 | grep -q 'clean'"
    run_test "No errors from e2fsck" "e2fsck -f -n cs111-base.img 2>&1 | grep -v 'clean' | grep -qv 'ERROR'"
elif command -v fsck.ext2 &> /dev/null; then
    run_test "fsck.ext2 reports clean" "fsck.ext2 -f -n cs111-base.img 2>&1 | grep -q 'clean'"
else
    echo -e "${YELLOW}No ext2 fsck tool found - skipping fsck tests${NC}"
fi
echo ""

# Advanced structure tests
echo "Step 8: Advanced Structure Tests"
echo "---------------------------------"

# Check volume name
run_test "Volume name is cs111-base" "dd if=cs111-base.img bs=1 skip=1144 count=10 2>/dev/null | grep -q 'cs111-base'"

# Check directory structure
run_test "Root dir at block 21" "hexdump -s 21504 -n 4 -e '1/4 \"%u\"' cs111-base.img | grep -q '^2$'"

# Check for proper symlink
run_test "Symlink target stored" "dd if=cs111-base.img bs=1 skip=6656 count=11 2>/dev/null | grep -q 'hello-world'"

echo ""

# Mount test (requires sudo and Linux)
echo "Step 9: Mount Test (Optional)"
echo "-----------------------------"
if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v sudo &> /dev/null; then
    if sudo -n true 2>/dev/null; then
        mkdir -p test_mnt
        if sudo mount -o loop cs111-base.img test_mnt 2>/dev/null; then
            run_test "Mount successful" "true"
            run_test "Files visible" "ls test_mnt | grep -q hello-world"
            run_test "Symlink works" "test -L test_mnt/hello"
            run_test "File readable" "cat test_mnt/hello-world | grep -q 'Hello world'"
            sudo umount test_mnt 2>/dev/null
        else
            echo -e "${YELLOW}Mount failed - may need root permissions${NC}"
        fi
        rmdir test_mnt 2>/dev/null
    else
        echo -e "${YELLOW}Sudo access required for mount test${NC}"
    fi
else
    echo -e "${YELLOW}Mount test only available on Linux with sudo${NC}"
fi
echo ""

# Summary
echo "========================================="
echo "              TEST SUMMARY"
echo "========================================="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$((TOTAL_TESTS - PASSED_TESTS))${NC}"

PERCENTAGE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo -e "Score: $PERCENTAGE%"

if [ $PERCENTAGE -eq 100 ]; then
    echo -e "${GREEN}Perfect Score! All tests passed!${NC}"
elif [ $PERCENTAGE -ge 90 ]; then
    echo -e "${GREEN}Excellent! Most tests passed.${NC}"
elif [ $PERCENTAGE -ge 70 ]; then
    echo -e "${YELLOW}Good, but some issues remain.${NC}"
else
    echo -e "${RED}Significant issues detected.${NC}"
fi

echo ""
echo "========================================="

# Return exit code based on success
if [ $PERCENTAGE -ge 90 ]; then
    exit 0
else
    exit 1
fi
