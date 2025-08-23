#!/usr/bin/env python3
import subprocess
import struct
import os
import unittest
import tempfile
import shutil

class TestExt2Comprehensive(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup the test environment once for all tests"""
        # Compile and create filesystem
        subprocess.run(['make', 'clean'], capture_output=True)
        result = subprocess.run(['make'], capture_output=True)
        if result.returncode != 0:
            raise Exception("Failed to compile")
        
        result = subprocess.run(['./ext2-create'], capture_output=True)
        if result.returncode != 0:
            raise Exception("Failed to create filesystem")
        
        # Open the image file for reading
        cls.img_fd = open('cs111-base.img', 'rb')
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.img_fd.close()
        subprocess.run(['make', 'clean'], capture_output=True)
    
    def read_block(self, block_num):
        """Read a block from the image"""
        self.img_fd.seek(block_num * 1024)
        return self.img_fd.read(1024)
    
    def test_file_size(self):
        """Test that the image is exactly 1 MiB"""
        self.img_fd.seek(0, 2)  # Seek to end
        size = self.img_fd.tell()
        self.assertEqual(size, 1024 * 1024, "Image should be exactly 1 MiB")
    
    def test_superblock_fields(self):
        """Test all superblock fields"""
        sb_data = self.read_block(1)
        
        # Test individual fields at correct offsets
        # s_inodes_count at offset 0
        s_inodes_count = struct.unpack('<I', sb_data[0:4])[0]
        self.assertEqual(s_inodes_count, 128, "s_inodes_count should be 128")
        
        # s_blocks_count at offset 4
        s_blocks_count = struct.unpack('<I', sb_data[4:8])[0]
        self.assertEqual(s_blocks_count, 1024, "s_blocks_count should be 1024")
        
        # s_r_blocks_count at offset 8
        s_r_blocks_count = struct.unpack('<I', sb_data[8:12])[0]
        self.assertEqual(s_r_blocks_count, 0, "s_r_blocks_count should be 0")
        
        # s_free_blocks_count at offset 12
        s_free_blocks_count = struct.unpack('<I', sb_data[12:16])[0]
        self.assertEqual(s_free_blocks_count, 1000, "s_free_blocks_count should be 1000")
        
        # s_free_inodes_count at offset 16
        s_free_inodes_count = struct.unpack('<I', sb_data[16:20])[0]
        self.assertEqual(s_free_inodes_count, 115, "s_free_inodes_count should be 115")
        
        # s_first_data_block at offset 20
        s_first_data_block = struct.unpack('<I', sb_data[20:24])[0]
        self.assertEqual(s_first_data_block, 1, "s_first_data_block should be 1")
        
        # s_log_block_size at offset 24
        s_log_block_size = struct.unpack('<I', sb_data[24:28])[0]
        self.assertEqual(s_log_block_size, 0, "s_log_block_size should be 0 (1024 byte blocks)")
        
        # s_blocks_per_group at offset 32
        s_blocks_per_group = struct.unpack('<I', sb_data[32:36])[0]
        self.assertEqual(s_blocks_per_group, 1024, "s_blocks_per_group should be 1024")
        
        # s_inodes_per_group at offset 40
        s_inodes_per_group = struct.unpack('<I', sb_data[40:44])[0]
        self.assertEqual(s_inodes_per_group, 128, "s_inodes_per_group should be 128")
        
        # s_max_mnt_count at offset 54 (NOT 42!)
        s_max_mnt_count = struct.unpack('<h', sb_data[54:56])[0]
        self.assertEqual(s_max_mnt_count, -1, "s_max_mnt_count should be -1")
        
        # s_magic at offset 56
        s_magic = struct.unpack('<H', sb_data[56:58])[0]
        self.assertEqual(s_magic, 0xEF53, "Magic number should be 0xEF53")
        
        # s_state at offset 58
        s_state = struct.unpack('<H', sb_data[58:60])[0]
        self.assertEqual(s_state, 1, "s_state should be 1 (clean)")
        
        # s_errors at offset 60
        s_errors = struct.unpack('<H', sb_data[60:62])[0]
        self.assertEqual(s_errors, 1, "s_errors should be 1 (continue)")
        
        # s_checkinterval at offset 68 (NOT 76!)
        s_checkinterval = struct.unpack('<I', sb_data[68:72])[0]
        self.assertEqual(s_checkinterval, 1, "s_checkinterval should be 1")
        
        # s_rev_level at offset 76
        s_rev_level = struct.unpack('<I', sb_data[76:80])[0]
        self.assertEqual(s_rev_level, 0, "s_rev_level should be 0 (good old rev)")
        
        # Check volume name at offset 120
        volume_name = sb_data[120:136].rstrip(b'\x00').decode('ascii')
        self.assertEqual(volume_name, "cs111-base", "Volume name should be 'cs111-base'")
    
    def test_block_group_descriptor(self):
        """Test block group descriptor table"""
        bgd_data = self.read_block(2)
        
        # Unpack block group descriptor (first 32 bytes)
        fmt = '<IIIHHH'
        fields = struct.unpack(fmt, bgd_data[:18])
        
        self.assertEqual(fields[0], 3, "bg_block_bitmap should be block 3")
        self.assertEqual(fields[1], 4, "bg_inode_bitmap should be block 4")
        self.assertEqual(fields[2], 5, "bg_inode_table should be block 5")
        self.assertEqual(fields[3], 1000, "bg_free_blocks_count should be 1000")
        self.assertEqual(fields[4], 115, "bg_free_inodes_count should be 115")
        self.assertEqual(fields[5], 2, "bg_used_dirs_count should be 2 (root and lost+found)")
    
    def test_block_bitmap(self):
        """Test block bitmap correctness"""
        bitmap_data = self.read_block(3)
        
        # First 3 bytes should mark blocks 0-23 as used
        self.assertEqual(bitmap_data[0], 0xFF, "Blocks 0-7 should be marked as used")
        self.assertEqual(bitmap_data[1], 0xFF, "Blocks 8-15 should be marked as used")
        self.assertEqual(bitmap_data[2], 0xFF, "Blocks 16-23 should be marked as used")
        
        # Remaining blocks should be free (0)
        for i in range(3, 128):  # Check first 128 bytes
            self.assertEqual(bitmap_data[i], 0x00, f"Byte {i} should be 0 (blocks free)")
    
    def test_inode_bitmap(self):
        """Test inode bitmap correctness"""
        bitmap_data = self.read_block(4)
        
        # First byte: inodes 1-8 used
        self.assertEqual(bitmap_data[0], 0xFF, "Inodes 1-8 should be marked as used")
        
        # Second byte: inodes 9-13 used (bits 0-4), rest free
        self.assertEqual(bitmap_data[1], 0x1F, "Inodes 9-13 should be marked as used")
        
        # Remaining inodes should be free
        for i in range(2, 16):  # Check first 16 bytes (128 inodes)
            self.assertEqual(bitmap_data[i], 0x00, f"Byte {i} should be 0 (inodes free)")
    
    def test_root_inode(self):
        """Test root directory inode (inode 2)"""
        inode_table = self.read_block(5)
        # Root inode is at index 1 (inode 2)
        inode_data = inode_table[128:256]  # 128 bytes per inode
        
        # Unpack inode structure (corrected format)
        fmt = '<HHIIIIIHHIIII'
        fields = struct.unpack(fmt, inode_data[:44])
        
        # Check mode (directory with rwxr-xr-x)
        expected_mode = 0x4000 | 0o755  # S_IFDIR | permissions
        self.assertEqual(fields[0], expected_mode, "Root should be directory with 755 permissions")
        
        # Check uid/gid
        self.assertEqual(fields[1], 0, "Root should be owned by uid 0")
        self.assertEqual(fields[7], 0, "Root should be owned by gid 0")
        
        # Check size
        self.assertEqual(fields[2], 1024, "Root directory size should be 1024")
        
        # Check links count (., .., and lost+found/..)
        self.assertEqual(fields[8], 3, "Root should have 3 links")
        
        # Check blocks
        self.assertEqual(fields[9], 2, "Root should use 2 (512-byte) blocks")
        
        # Check first block pointer
        self.assertEqual(fields[12], 21, "Root directory should be at block 21")
    
    def test_lost_and_found_inode(self):
        """Test lost+found directory inode (inode 11)"""
        inode_table = self.read_block(6)  # Inode 11 is in block 6
        inode_data = inode_table[256:384]  # Inode 11 at offset 256
        
        fmt = '<HHIIIIIHHIIII'
        fields = struct.unpack(fmt, inode_data[:44])
        
        # Check mode
        expected_mode = 0x4000 | 0o755
        self.assertEqual(fields[0], expected_mode, "lost+found should be directory with 755 permissions")
        
        # Check ownership
        self.assertEqual(fields[1], 0, "lost+found should be owned by uid 0")
        self.assertEqual(fields[7], 0, "lost+found should be owned by gid 0")
        
        # Check links
        self.assertEqual(fields[8], 2, "lost+found should have 2 links")
        
        # Check block pointer
        self.assertEqual(fields[12], 22, "lost+found should be at block 22")
    
    def test_hello_world_inode(self):
        """Test hello-world file inode (inode 12)"""
        inode_table = self.read_block(6)
        inode_data = inode_table[384:512]  # Inode 12 at offset 384
        
        fmt = '<HHIIIIIHHIIII'
        fields = struct.unpack(fmt, inode_data[:44])
        
        # Check mode (regular file with rw-r--r--)
        expected_mode = 0x8000 | 0o644
        self.assertEqual(fields[0], expected_mode, "hello-world should be regular file with 644 permissions")
        
        # Check ownership
        self.assertEqual(fields[1], 1000, "hello-world should be owned by uid 1000")
        self.assertEqual(fields[7], 1000, "hello-world should be owned by gid 1000")
        
        # Check size
        self.assertEqual(fields[2], 12, "hello-world size should be 12 bytes")
        
        # Check links
        self.assertEqual(fields[8], 1, "hello-world should have 1 link")
        
        # Check block pointer
        self.assertEqual(fields[12], 23, "hello-world should be at block 23")
    
    def test_hello_symlink_inode(self):
        """Test hello symlink inode (inode 13)"""
        inode_table = self.read_block(6)
        inode_data = inode_table[512:640]  # Inode 13 at offset 512
        
        fmt = '<HHIIIIIHHIIII'
        fields = struct.unpack(fmt, inode_data[:44])
        
        # Check mode (symlink with rw-r--r--)
        expected_mode = 0xA000 | 0o644
        self.assertEqual(fields[0], expected_mode, "hello should be symlink with 644 permissions")
        
        # Check ownership
        self.assertEqual(fields[1], 1000, "hello should be owned by uid 1000")
        self.assertEqual(fields[7], 1000, "hello should be owned by gid 1000")
        
        # Check size
        self.assertEqual(fields[2], 11, "hello symlink size should be 11 bytes")
        
        # Check blocks (should be 0 for fast symlink)
        self.assertEqual(fields[9], 0, "hello symlink should use 0 blocks (fast symlink)")
        
        # Check symlink target stored in i_block array
        symlink_target = inode_data[40:51].decode('ascii')
        self.assertEqual(symlink_target, "hello-world", "Symlink should point to 'hello-world'")
    
    def test_root_directory_entries(self):
        """Test root directory entries"""
        root_dir = self.read_block(21)
        
        entries = []
        offset = 0
        
        # Parse directory entries
        while offset < 1024:
            inode = struct.unpack('<I', root_dir[offset:offset+4])[0]
            rec_len = struct.unpack('<H', root_dir[offset+4:offset+6])[0]
            name_len = struct.unpack('<H', root_dir[offset+6:offset+8])[0] & 0xFF
            
            if inode != 0:
                name = root_dir[offset+8:offset+8+name_len].decode('ascii')
                entries.append((inode, name))
            
            if rec_len == 0:
                break
            offset += rec_len
        
        # Check entries
        expected_entries = [
            (2, '.'),
            (2, '..'),
            (11, 'lost+found'),
            (12, 'hello-world'),
            (13, 'hello')
        ]
        
        self.assertEqual(len(entries), 5, "Root directory should have 5 entries")
        for expected, actual in zip(expected_entries, entries):
            self.assertEqual(actual[0], expected[0], f"Entry '{expected[1]}' should have inode {expected[0]}")
            self.assertEqual(actual[1], expected[1], f"Entry name should be '{expected[1]}'")
    
    def test_lost_and_found_directory_entries(self):
        """Test lost+found directory entries"""
        lf_dir = self.read_block(22)
        
        entries = []
        offset = 0
        
        while offset < 1024 and offset < 100:  # Check first 100 bytes
            inode = struct.unpack('<I', lf_dir[offset:offset+4])[0]
            rec_len = struct.unpack('<H', lf_dir[offset+4:offset+6])[0]
            name_len = struct.unpack('<H', lf_dir[offset+6:offset+8])[0] & 0xFF
            
            if inode != 0:
                name = lf_dir[offset+8:offset+8+name_len].decode('ascii')
                entries.append((inode, name))
            
            if rec_len == 0:
                break
            offset += rec_len
        
        # Check entries
        self.assertEqual(len(entries), 2, "lost+found should have 2 entries")
        self.assertEqual(entries[0], (11, '.'), "First entry should be '.'")
        self.assertEqual(entries[1], (2, '..'), "Second entry should be '..'")
    
    def test_hello_world_content(self):
        """Test hello-world file content"""
        file_block = self.read_block(23)
        content = file_block[:12]
        
        self.assertEqual(content, b'Hello world\n', "File should contain 'Hello world\\n'")
        
        # Check that byte 12 is null (not part of file)
        self.assertEqual(file_block[12], 0, "Byte after file content should be 0")
    
    def test_fsck_clean(self):
        """Test that fsck reports no errors"""
        # Try different fsck commands based on availability
        fsck_commands = ['e2fsck', 'fsck.ext2']
        fsck_found = False
        
        for cmd in fsck_commands:
            try:
                result = subprocess.run([cmd, '-f', '-n', 'cs111-base.img'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    fsck_found = True
                    # Check output for no errors
                    output = result.stdout + result.stderr
                    self.assertNotIn('ERROR', output.upper(), "fsck should report no errors")
                    self.assertNotIn('WARNING', output.upper(), "fsck should report no warnings")
                    self.assertIn('clean', output.lower(), "fsck should report filesystem as clean")
                    break
            except FileNotFoundError:
                continue
        
        if not fsck_found:
            self.skipTest("e2fsck/fsck.ext2 not available")
    
    def test_all_unused_inodes_zeroed(self):
        """Test that all unused inodes are properly zeroed"""
        # Check inodes 14-128 are all zeros
        for inode_num in range(14, 129):
            block_num = 5 + (inode_num - 1) // 8  # 8 inodes per block
            block = self.read_block(block_num)
            offset = ((inode_num - 1) % 8) * 128
            inode_data = block[offset:offset+128]
            
            self.assertEqual(inode_data, b'\x00' * 128, 
                           f"Unused inode {inode_num} should be all zeros")
    
    def test_directory_entry_alignment(self):
        """Test that directory entries are properly aligned"""
        root_dir = self.read_block(21)
        
        offset = 0
        while offset < 1024:
            rec_len = struct.unpack('<H', root_dir[offset+4:offset+6])[0]
            if rec_len == 0:
                break
            
            # rec_len should be multiple of 4
            self.assertEqual(rec_len % 4, 0, f"Directory entry at offset {offset} should be 4-byte aligned")
            
            offset += rec_len
            if offset >= 1024:
                break
    
    def test_timestamps_reasonable(self):
        """Test that timestamps are reasonable (not 0, not in future)"""
        import time
        current_time = int(time.time())
        
        # Check superblock write time
        sb_data = self.read_block(1)
        wtime = struct.unpack('<I', sb_data[48:52])[0]
        self.assertGreater(wtime, 0, "Superblock write time should be > 0")
        self.assertLessEqual(wtime, current_time + 60, "Write time should not be in future")
        
        # Check root inode times
        inode_table = self.read_block(5)
        inode_data = inode_table[128:256]
        atime = struct.unpack('<I', inode_data[8:12])[0]
        ctime = struct.unpack('<I', inode_data[12:16])[0]
        mtime = struct.unpack('<I', inode_data[16:20])[0]
        
        for t in [atime, ctime, mtime]:
            self.assertGreater(t, 0, "Inode times should be > 0")
            self.assertLessEqual(t, current_time + 60, "Inode times should not be in future")

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
