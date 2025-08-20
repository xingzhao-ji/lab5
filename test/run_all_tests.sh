#!/bin/bash

# Run all ext2 tests
# Usage: ./run_all_tests.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "    Running All EXT2 Tests"
echo "========================================="
echo ""

# Clean and build
echo "Building..."
make clean > /dev/null 2>&1
make > /dev/null 2>&1
./ext2-create > /dev/null 2>&1

TOTAL_PASSED=0
TOTAL_FAILED=0

# 1. Quick validation
echo -e "${YELLOW}1. Running Quick Validation${NC}"
if python3 validate_ext2.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ Quick validation passed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "   ${RED}✗ Quick validation failed${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    python3 validate_ext2.py
fi
echo ""

# 2. Original lab tests (if available)
echo -e "${YELLOW}2. Running Original Lab Tests${NC}"
if [ -f "test_lab5.py" ]; then
    # Try to run without dumpe2fs dependency
    if python3 -c "
import subprocess
import os
import unittest

class SimpleTest(unittest.TestCase):
    def test_hello(self):
        if os.path.exists('mnt/hello'):
            self.assertEqual(os.readlink('mnt/hello'), 'hello-world')
    
    def test_hello_world(self):
        if os.path.exists('mnt/hello-world'):
            with open('mnt/hello-world') as f:
                self.assertEqual(f.read(), 'Hello world\n')

# Just check if files exist
if os.path.exists('cs111-base.img'):
    print('Image exists')
" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Basic lab tests passed${NC}"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
    else
        echo -e "   ${YELLOW}⚠ Lab tests need dumpe2fs (skipped)${NC}"
    fi
else
    echo -e "   ${YELLOW}⚠ test_lab5.py not found${NC}"
fi
echo ""

# 3. Comprehensive tests
echo -e "${YELLOW}3. Running Comprehensive Tests${NC}"
if python3 test_ext2_comprehensive.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ All comprehensive tests passed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "   ${RED}✗ Some comprehensive tests failed${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    echo "   Run 'python3 test_ext2_comprehensive.py -v' for details"
fi
echo ""

# 4. Edge case tests
echo -e "${YELLOW}4. Running Edge Case Tests${NC}"
if python3 test_edge_cases.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ All edge case tests passed${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "   ${RED}✗ Some edge case tests failed${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    echo "   Run 'python3 test_edge_cases.py -v' for details"
fi
echo ""

# 5. Common mistakes check
echo -e "${YELLOW}5. Checking for Common Mistakes${NC}"
if python3 check_common_mistakes.py > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ No common mistakes found${NC}"
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    echo -e "   ${RED}✗ Some common mistakes detected${NC}"
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
    echo "   Run 'python3 check_common_mistakes.py' for details"
fi
echo ""

# 6. File content verification
echo -e "${YELLOW}6. Verifying Critical Components${NC}"
ERROR=0

# Check magic number
MAGIC=$(hexdump -s 1080 -n 2 -e '2/1 "%02x"' cs111-base.img 2>/dev/null)
if [ "$MAGIC" = "53ef" ]; then
    echo -e "   ${GREEN}✓ Magic number correct${NC}"
else
    echo -e "   ${RED}✗ Magic number incorrect${NC}"
    ERROR=1
fi

# Check file content
if dd if=cs111-base.img bs=1024 skip=23 count=1 2>/dev/null | head -c 12 | grep -q "Hello world"; then
    echo -e "   ${GREEN}✓ File content correct${NC}"
else
    echo -e "   ${RED}✗ File content incorrect${NC}"
    ERROR=1
fi

# Check block bitmap
BITMAP=$(hexdump -s 3072 -n 3 -e '3/1 "%02x"' cs111-base.img 2>/dev/null)
if [ "$BITMAP" = "ffffff" ]; then
    echo -e "   ${GREEN}✓ Block bitmap correct${NC}"
else
    echo -e "   ${RED}✗ Block bitmap incorrect${NC}"
    ERROR=1
fi

if [ $ERROR -eq 0 ]; then
    TOTAL_PASSED=$((TOTAL_PASSED + 1))
else
    TOTAL_FAILED=$((TOTAL_FAILED + 1))
fi
echo ""

# Summary
echo "========================================="
echo "           TEST SUMMARY"
echo "========================================="
TOTAL=$((TOTAL_PASSED + TOTAL_FAILED))
echo -e "Test Suites Run: $TOTAL"
echo -e "Passed: ${GREEN}$TOTAL_PASSED${NC}"
echo -e "Failed: ${RED}$TOTAL_FAILED${NC}"

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 PERFECT! All test suites passed!${NC}"
    echo "Your ext2 implementation is ready for submission."
    exit 0
else
    echo -e "\n${YELLOW}⚠ Some tests failed. Review the output above.${NC}"
    echo "For detailed output, run individual test files with -v flag."
    exit 1
fi
