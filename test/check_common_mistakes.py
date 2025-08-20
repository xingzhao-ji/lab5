#!/usr/bin/env python3
"""
Check for common mistakes in ext2 implementation
"""

import subprocess
import struct
import sys

def check_mistake(condition, error_msg, warning=False):
    """Helper to check for mistakes"""
    if not condition:
        prefix = "WARNING" if warning else "ERROR"
        print(f"[{prefix}] {error_msg}")
        return False
    return True

def main():
    # Compile and create filesystem
    subprocess.run(['make', 'clean'], capture_output=True)
    subprocess.run(['make'], capture_output=True)
    subprocess.run(['./ext2-create'], capture_output=True)
    
    errors = 0
    warnings = 0
    
    print("Checking for common mistakes in ext2 implementation...")
    print("=" * 50)
    
    with open('cs111-base.img', 'rb') as f:
        # Read entire image
        f.seek(0)
        img_data = f.read()
        
        # 1. Check superblock location
        print("\n1. Checking superblock placement...")
        sb_magic = struct.unpack('<H', img_data[1080:1082])[0]
        if not check_mistake(sb_magic == 0xEF53, 
                           "Superblock not at block 1 or magic number wrong"):
            errors += 1
        else:
            print("   ✓ Superblock correctly placed at block 1")
        
        # 2. Check for common off-by-one errors
        print("\n2. Checking for off-by-one errors...")
        
        # Check first data block
        first_data_block = struct.unpack('<I', img_data[1044:1048])[0]
        if not check_mistake(first_data_block == 1, 
                           f"s_first_data_block should be 1, got {first_data_block}"):
            errors += 1
        else:
            print("   ✓ First data block correctly set to 1")
        
        # 3. Check block size settings
        print("\n3. Checking block size configuration...")
        log_block_size = struct.unpack('<I', img_data[1048:1052])[0]
        if not check_mistake(log_block_size == 0,
                           f"s_log_block_size should be 0 for 1024-byte blocks, got {log_block_size}"):
            errors += 1
        else:
            print("   ✓ Block size correctly set to 1024 bytes")
        
        # 4. Check inode bitmap - common mistake is wrong bit order
        print("\n4. Checking inode bitmap bit order...")
        inode_bitmap = img_data[4096:4098]
        
        # Should have inodes 1-13 marked as used
        expected_byte0 = 0xFF  # Inodes 1-8
        expected_byte1 = 0x1F  # Inodes 9-13
        
        if inode_bitmap[0] != expected_byte0:
            print(f"   ERROR: Inode bitmap byte 0 should be 0xFF, got 0x{inode_bitmap[0]:02X}")
            print("   (Possible bit order issue)")
            errors += 1
        else:
            print("   ✓ Inode bitmap byte 0 correct")
            
        if inode_bitmap[1] != expected_byte1:
            print(f"   ERROR: Inode bitmap byte 1 should be 0x1F, got 0x{inode_bitmap[1]:02X}")
            errors += 1
        else:
            print("   ✓ Inode bitmap byte 1 correct")
        
        # 5. Check directory entry structure
        print("\n5. Checking directory entry structure...")
        root_dir = img_data[21504:22528]  # Block 21
        
        # Check first entry (should be '.')
        first_inode = struct.unpack('<I', root_dir[0:4])[0]
        first_rec_len = struct.unpack('<H', root_dir[4:6])[0]
        first_name_len = root_dir[6]
        
        if not check_mistake(first_inode == 2, 
                           f"First entry in root should have inode 2, got {first_inode}"):
            errors += 1
        
        if not check_mistake(first_name_len == 1,
                           f"First entry name length should be 1 for '.', got {first_name_len}"):
            errors += 1
        
        # 6. Check for hardcoded vs calculated values
        print("\n6. Checking for hardcoded values...")
        
        free_blocks = struct.unpack('<I', img_data[1036:1040])[0]
        free_inodes = struct.unpack('<I', img_data[1040:1044])[0]
        
        if not check_mistake(free_blocks == 1000,
                           f"Free blocks should be 1000 (NUM_FREE_BLOCKS), got {free_blocks}"):
            errors += 1
        else:
            print("   ✓ Free blocks count correct")
            
        if not check_mistake(free_inodes == 115,
                           f"Free inodes should be 115 (NUM_FREE_INODES), got {free_inodes}"):
            errors += 1
        else:
            print("   ✓ Free inodes count correct")
        
        # 7. Check symlink implementation
        print("\n7. Checking symlink implementation...")
        
        # Inode 13 (hello symlink) - at offset 512 in block 6
        hello_inode = img_data[6656:6784]
        hello_mode = struct.unpack('<H', hello_inode[0:2])[0]
        hello_size = struct.unpack('<I', hello_inode[4:8])[0]
        hello_blocks = struct.unpack('<I', hello_inode[28:32])[0]
        
        if not check_mistake((hello_mode & 0xF000) == 0xA000,
                           f"Symlink mode should have S_IFLNK (0xA000), got 0x{hello_mode:04X}"):
            errors += 1
        else:
            print("   ✓ Symlink mode correct")
            
        if not check_mistake(hello_size == 11,
                           f"Symlink size should be 11, got {hello_size}"):
            errors += 1
        else:
            print("   ✓ Symlink size correct")
            
        if not check_mistake(hello_blocks == 0,
                           f"Fast symlink should have 0 blocks, got {hello_blocks}"):
            errors += 1
        else:
            print("   ✓ Fast symlink blocks correct")
        
        # Check symlink target in i_block
        symlink_target = hello_inode[40:51]
        if not check_mistake(symlink_target == b'hello-world',
                           f"Symlink target should be 'hello-world', got {symlink_target}"):
            errors += 1
        else:
            print("   ✓ Symlink target stored correctly in i_block")
        
        # 8. Check file permissions
        print("\n8. Checking file permissions...")
        
        # Root inode (inode 2)
        root_inode = img_data[5248:5376]
        root_mode = struct.unpack('<H', root_inode[0:2])[0]
        root_perms = root_mode & 0o777
        
        if not check_mistake(root_perms == 0o755,
                           f"Root directory should have 755 permissions, got {oct(root_perms)}"):
            errors += 1
        else:
            print("   ✓ Root directory permissions correct")
        
        # hello-world file (inode 12)
        hw_inode = img_data[6528:6656]
        hw_mode = struct.unpack('<H', hw_inode[0:2])[0]
        hw_perms = hw_mode & 0o777
        
        if not check_mistake(hw_perms == 0o644,
                           f"hello-world should have 644 permissions, got {oct(hw_perms)}"):
            errors += 1
        else:
            print("   ✓ hello-world file permissions correct")
        
        # 9. Check timestamps
        print("\n9. Checking timestamps...")
        
        wtime = struct.unpack('<I', img_data[1072:1076])[0]
        lastcheck = struct.unpack('<I', img_data[1088:1092])[0]
        
        if not check_mistake(wtime > 0, "Write time should be set"):
            errors += 1
        if not check_mistake(lastcheck > 0, "Last check time should be set"):
            errors += 1
        
        if wtime > 0 and lastcheck > 0:
            print("   ✓ Timestamps are set")
        
        # 10. Check link counts
        print("\n10. Checking link counts...")
        
        root_links = struct.unpack('<H', root_inode[26:28])[0]
        if not check_mistake(root_links == 3,
                           f"Root should have 3 links (., .., lost+found/..), got {root_links}"):
            errors += 1
        else:
            print("   ✓ Root directory link count correct")
        
        # 11. Check for zero padding
        print("\n11. Checking for proper zero padding...")
        
        # Check unused portion of superblock
        sb_reserved = img_data[1160:2048]
        if not all(b == 0 for b in sb_reserved):
            print("   WARNING: Superblock reserved area not fully zeroed")
            warnings += 1
        else:
            print("   ✓ Superblock padding correct")
        
        # 12. Check hello world file content
        print("\n12. Checking file content...")
        
        hw_content = img_data[23552:23564]
        if not check_mistake(hw_content == b'Hello world\n',
                           f"File content should be 'Hello world\\n', got {hw_content}"):
            errors += 1
        else:
            print("   ✓ File content correct")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"  Errors found: {errors}")
    print(f"  Warnings: {warnings}")
    
    if errors == 0:
        print("\n✅ No critical errors found!")
        if warnings == 0:
            print("   Perfect implementation!")
        return 0
    else:
        print(f"\n❌ Found {errors} error(s) that need fixing")
        return 1

if __name__ == '__main__':
    sys.exit(main())
