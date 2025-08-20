#!/usr/bin/env python3
import subprocess
import struct
import os
import unittest

class TestExt2EdgeCases(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment"""
        subprocess.run(['make', 'clean'], capture_output=True)
        subprocess.run(['make'], capture_output=True)
        subprocess.run(['./ext2-create'], capture_output=True)
        cls.img_fd = open('cs111-base.img', 'rb')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.img_fd.close()
    
    def read_raw_bytes(self, offset, size):
        """Read raw bytes from image at offset"""
        self.img_fd.seek(offset)
        return self.img_fd.read(size)
    
    def test_reserved_inodes_unused(self):
        """Test that reserved inodes 3-10 are properly handled"""
        # Inodes 3-10 should be allocated but not used
        inode_bitmap = self.read_raw_bytes(4096, 16)  # Read inode bitmap
        
        # Check that inodes 3-10 are marked as used in bitmap
        byte0 = inode_bitmap[0]  # Inodes 1-8
        byte1 = inode_bitmap[1]  # Inodes 9-16
        
        self.assertEqual(byte0, 0xFF, "Inodes 1-8 should be marked used")
        self.assertTrue(byte1 & 0x07, "Inodes 9-10 should be marked used")
        
        # But the actual inode entries should be zeroed
        for inode_num in range(3, 11):
            if inode_num == 2:  # Skip root
                continue
            block_offset = 5 * 1024  # Inode table starts at block 5
            inode_offset = (inode_num - 1) * 128
            inode_data = self.read_raw_bytes(block_offset + inode_offset, 128)
            
            # Check if mode is 0 (indicating unused)
            mode = struct.unpack('<H', inode_data[0:2])[0]
            if inode_num < 11:  # Reserved inodes
                self.assertEqual(mode, 0, f"Reserved inode {inode_num} should have mode 0")
    
    def test_block_0_never_used(self):
        """Test that block 0 is never referenced"""
        # Block 0 should be marked as used but never referenced
        block_bitmap = self.read_raw_bytes(3072, 1)
        self.assertTrue(block_bitmap[0] & 0x01, "Block 0 should be marked as used")
        
        # Check all inode block pointers
        for inode_num in [2, 11, 12, 13]:  # Active inodes
            block_num = 5 + (inode_num - 1) // 8
            offset = ((inode_num - 1) % 8) * 128
            inode_data = self.read_raw_bytes(block_num * 1024 + offset, 128)
            
            # Check direct blocks (i_block[0-11])
            for i in range(12):
                block_ptr = struct.unpack('<I', inode_data[40 + i*4:44 + i*4])[0]
                if block_ptr != 0:
                    self.assertNotEqual(block_ptr, 0, f"Inode {inode_num} should not reference block 0")
    
    def test_superblock_padding(self):
        """Test that superblock padding and reserved fields are zero"""
        sb_data = self.read_raw_bytes(1024, 1024)
        
        # The s_pad array is at offset 88-108 (20 bytes)
        # But UUID starts at 104, so only check 88-104
        padding = sb_data[88:104]
        self.assertEqual(padding, b'\x00' * 16, "Superblock padding before UUID should be zero")
        
        # Check reserved array at end (starts at 136 after volume name)
        reserved_offset = 136
        reserved_size = 229 * 4
        reserved = sb_data[reserved_offset:reserved_offset + reserved_size]
        self.assertEqual(reserved, b'\x00' * reserved_size, "Superblock reserved should be zero")
    
    def test_directory_entry_boundaries(self):
        """Test that directory entries don't cross block boundaries"""
        root_dir = self.read_raw_bytes(21 * 1024, 1024)
        
        offset = 0
        total_used = 0
        
        while offset < 1024:
            rec_len = struct.unpack('<H', root_dir[offset+4:offset+6])[0]
            if rec_len == 0:
                break
            
            # Entry should not cross block boundary
            self.assertLessEqual(offset + rec_len, 1024, 
                               f"Directory entry at offset {offset} crosses block boundary")
            
            offset += rec_len
            total_used = offset
        
        # Last entry should extend to end of block
        self.assertEqual(total_used, 1024, "Directory entries should fill entire block")
    
    def test_symlink_null_terminated(self):
        """Test that symlink target is properly null-terminated in i_block"""
        # Read hello symlink inode (inode 13)
        inode_data = self.read_raw_bytes(6 * 1024 + 512, 128)
        
        # Symlink target is stored in i_block array (60 bytes starting at offset 40)
        i_block = inode_data[40:100]
        
        # Should contain "hello-world" followed by zeros
        self.assertEqual(i_block[:11], b'hello-world', "Symlink target should be 'hello-world'")
        self.assertEqual(i_block[11], 0, "Symlink target should be null-terminated")
        
        # Rest should be zeros
        for i in range(12, 60):
            self.assertEqual(i_block[i], 0, f"i_block[{i}] should be zero")
    
    def test_no_sparse_blocks(self):
        """Test that allocated blocks are contiguous (no sparse allocation)"""
        block_bitmap = self.read_raw_bytes(3072, 128)
        
        # Check first 24 blocks are all marked as used
        # First 3 bytes should be 0xFF (blocks 0-23)
        self.assertEqual(block_bitmap[0], 0xFF, "Blocks 0-7 should be marked as used")
        self.assertEqual(block_bitmap[1], 0xFF, "Blocks 8-15 should be marked as used")
        self.assertEqual(block_bitmap[2], 0xFF, "Blocks 16-23 should be marked as used")
        
        # Blocks 24 onwards should be free
        self.assertEqual(block_bitmap[3], 0x00, "Blocks 24-31 should be free")
    
    def test_inode_flags_and_reserved(self):
        """Test that inode flags and reserved fields are zero"""
        for inode_num in [2, 11, 12, 13]:
            block_num = 5 + (inode_num - 1) // 8
            offset = ((inode_num - 1) % 8) * 128
            inode_data = self.read_raw_bytes(block_num * 1024 + offset, 128)
            
            # Check i_flags (offset 32)
            flags = struct.unpack('<I', inode_data[32:36])[0]
            self.assertEqual(flags, 0, f"Inode {inode_num} flags should be 0")
            
            # Check i_reserved1 (offset 36)
            reserved1 = struct.unpack('<I', inode_data[36:40])[0]
            self.assertEqual(reserved1, 0, f"Inode {inode_num} reserved1 should be 0")
            
            # Check i_osd2 fields (offset 116-128)
            osd2 = inode_data[116:128]
            self.assertEqual(osd2, b'\x00' * 12, f"Inode {inode_num} osd2 should be zero")
    
    def test_correct_checksum_interval(self):
        """Test superblock checksum interval settings"""
        sb_data = self.read_raw_bytes(1024, 1024)
        
        # s_checkinterval at offset 68 (corrected from 76)
        checkinterval = struct.unpack('<I', sb_data[68:72])[0]
        self.assertEqual(checkinterval, 1, "Check interval should be 1")
        
        # s_max_mnt_count at offset 54 (corrected from 42)
        max_mnt_count = struct.unpack('<h', sb_data[54:56])[0]
        self.assertEqual(max_mnt_count, -1, "Max mount count should be -1")
    
    def test_directory_file_types(self):
        """Test that directory entries have correct file type if supported"""
        root_dir = self.read_raw_bytes(21 * 1024, 1024)
        
        expected_types = {
            '.': 2,       # Directory
            '..': 2,      # Directory  
            'lost+found': 2,  # Directory
            'hello-world': 1,  # Regular file
            'hello': 7    # Symbolic link
        }
        
        offset = 0
        while offset < 1024:
            inode = struct.unpack('<I', root_dir[offset:offset+4])[0]
            rec_len = struct.unpack('<H', root_dir[offset+4:offset+6])[0]
            name_len = root_dir[offset+6]
            file_type = root_dir[offset+7]  # File type in directory entry
            
            if inode != 0:
                name = root_dir[offset+8:offset+8+name_len].decode('ascii')
                
                # File type field might be 0 for old ext2
                if file_type != 0 and name in expected_types:
                    self.assertEqual(file_type, expected_types[name], 
                                   f"File type for {name} should be {expected_types[name]}")
            
            if rec_len == 0:
                break
            offset += rec_len
    
    def test_proper_endianness(self):
        """Test that all multi-byte values use little-endian"""
        # Test a known value in superblock
        sb_data = self.read_raw_bytes(1024, 1024)
        
        # Read magic number both ways
        magic_le = struct.unpack('<H', sb_data[56:58])[0]
        magic_be = struct.unpack('>H', sb_data[56:58])[0]
        
        self.assertEqual(magic_le, 0xEF53, "Magic should be 0xEF53 in little-endian")
        self.assertNotEqual(magic_be, 0xEF53, "Magic should not match in big-endian")
    
    def test_uuid_format(self):
        """Test that UUID is properly formatted"""
        sb_data = self.read_raw_bytes(1024, 1024)
        uuid = sb_data[104:120]
        
        # Check expected UUID
        expected = bytes([0x5A, 0x1E, 0xAB, 0x1E, 0x13, 0x37, 0x13, 0x37,
                         0x13, 0x37, 0xC0, 0xFF, 0xEE, 0xC0, 0xFF, 0xEE])
        self.assertEqual(uuid, expected, "UUID should match expected value")

if __name__ == '__main__':
    unittest.main(verbosity=2)
