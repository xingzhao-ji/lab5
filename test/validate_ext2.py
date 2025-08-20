#!/usr/bin/env python3
"""
Simple validation script for ext2 implementation
Runs basic checks to ensure filesystem is correctly formatted
"""

import subprocess
import struct
import sys

def validate():
    print("EXT2 Filesystem Validation")
    print("=" * 40)
    
    # Compile and create
    print("Building filesystem...")
    subprocess.run(['make', 'clean'], capture_output=True)
    subprocess.run(['make'], capture_output=True)
    subprocess.run(['./ext2-create'], capture_output=True)
    
    errors = 0
    
    with open('cs111-base.img', 'rb') as f:
        # Test 1: File size
        f.seek(0, 2)
        size = f.tell()
        if size == 1048576:
            print("✓ File size: 1 MiB")
        else:
            print(f"✗ File size: {size} bytes (should be 1048576)")
            errors += 1
        
        # Test 2: Superblock magic
        f.seek(1080)
        magic = struct.unpack('<H', f.read(2))[0]
        if magic == 0xEF53:
            print("✓ Magic number: 0xEF53")
        else:
            print(f"✗ Magic number: 0x{magic:04x} (should be 0xEF53)")
            errors += 1
        
        # Test 3: Block and inode counts
        f.seek(1024)
        sb = f.read(88)
        
        inodes = struct.unpack('<I', sb[0:4])[0]
        blocks = struct.unpack('<I', sb[4:8])[0]
        free_blocks = struct.unpack('<I', sb[12:16])[0]
        free_inodes = struct.unpack('<I', sb[16:20])[0]
        
        if inodes == 128:
            print("✓ Inode count: 128")
        else:
            print(f"✗ Inode count: {inodes} (should be 128)")
            errors += 1
            
        if blocks == 1024:
            print("✓ Block count: 1024")
        else:
            print(f"✗ Block count: {blocks} (should be 1024)")
            errors += 1
            
        if free_blocks == 1000:
            print("✓ Free blocks: 1000")
        else:
            print(f"✗ Free blocks: {free_blocks} (should be 1000)")
            errors += 1
            
        if free_inodes == 115:
            print("✓ Free inodes: 115")
        else:
            print(f"✗ Free inodes: {free_inodes} (should be 115)")
            errors += 1
        
        # Test 4: Critical superblock fields
        f.seek(1024)
        sb = f.read(256)
        
        state = struct.unpack('<H', sb[58:60])[0]
        errors_field = struct.unpack('<H', sb[60:62])[0]
        max_mnt = struct.unpack('<h', sb[54:56])[0]
        checkint = struct.unpack('<I', sb[68:72])[0]
        
        if state == 1:
            print("✓ State: clean (1)")
        else:
            print(f"✗ State: {state} (should be 1)")
            errors += 1
            
        if errors_field == 1:
            print("✓ Errors: continue (1)")
        else:
            print(f"✗ Errors: {errors_field} (should be 1)")
            errors += 1
            
        if max_mnt == -1:
            print("✓ Max mount count: unlimited (-1)")
        else:
            print(f"✗ Max mount count: {max_mnt} (should be -1)")
            errors += 1
            
        if checkint == 1:
            print("✓ Check interval: 1 second")
        else:
            print(f"✗ Check interval: {checkint} (should be 1)")
            errors += 1
        
        # Test 5: Block bitmap
        f.seek(3072)
        bitmap = f.read(3)
        if bitmap == b'\xff\xff\xff':
            print("✓ Block bitmap: blocks 0-23 marked used")
        else:
            print(f"✗ Block bitmap: {bitmap.hex()} (should be ffffff)")
            errors += 1
        
        # Test 6: Inode bitmap
        f.seek(4096)
        bitmap = f.read(2)
        if bitmap == b'\xff\x1f':
            print("✓ Inode bitmap: inodes 1-13 marked used")
        else:
            print(f"✗ Inode bitmap: {bitmap.hex()} (should be ff1f)")
            errors += 1
        
        # Test 7: File content
        f.seek(23552)
        content = f.read(12)
        if content == b'Hello world\n':
            print("✓ File content: 'Hello world\\n'")
        else:
            print(f"✗ File content: {content} (should be b'Hello world\\n')")
            errors += 1
        
        # Test 8: Symlink target
        f.seek(6696)  # Inode 13's i_block field
        target = f.read(11)
        if target == b'hello-world':
            print("✓ Symlink target: 'hello-world'")
        else:
            print(f"✗ Symlink target: {target} (should be b'hello-world')")
            errors += 1
        
        # Test 9: Root directory first entry
        f.seek(21504)  # Block 21
        entry = f.read(12)
        inode = struct.unpack('<I', entry[0:4])[0]
        rec_len = struct.unpack('<H', entry[4:6])[0]
        name_len = entry[6]
        name = entry[8:8+name_len]
        
        if inode == 2 and name == b'.':
            print("✓ Root directory: first entry is '.'")
        else:
            print(f"✗ Root directory: first entry inode={inode}, name={name}")
            errors += 1
        
        # Test 10: Volume name
        f.seek(1144)  # 1024 + 120
        vol_name = f.read(10)
        if vol_name == b'cs111-base':
            print("✓ Volume name: 'cs111-base'")
        else:
            print(f"✗ Volume name: {vol_name} (should be b'cs111-base')")
            errors += 1
    
    print("\n" + "=" * 40)
    if errors == 0:
        print("✅ ALL TESTS PASSED!")
        print("Your implementation appears to be correct.")
        return 0
    else:
        print(f"❌ {errors} test(s) failed")
        print("Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(validate())
