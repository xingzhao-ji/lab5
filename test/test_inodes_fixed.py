# Save as test_inodes_fixed.py
import struct

with open('cs111-base.img', 'rb') as f:
    # Test root inode (inode 2)
    f.seek(5 * 1024 + 128)  # Block 5, offset 128
    inode = f.read(128)
    
    mode = struct.unpack('<H', inode[0:2])[0]
    uid = struct.unpack('<H', inode[2:4])[0]
    size = struct.unpack('<I', inode[4:8])[0]
    gid = struct.unpack('<H', inode[24:26])[0]
    links = struct.unpack('<H', inode[26:28])[0]
    blocks = struct.unpack('<I', inode[28:32])[0]
    block0 = struct.unpack('<I', inode[40:44])[0]
    
    print("Root inode:")
    print(f"  Mode: 0x{mode:04x} (should be 0x41ed = dir+755)")
    print(f"  UID: {uid} (should be 0)")
    print(f"  Size: {size} (should be 1024)")
    print(f"  GID: {gid} (should be 0)")
    print(f"  Links: {links} (should be 3)")
    print(f"  Block[0]: {block0} (should be 21)")
    
    # Test hello-world inode (inode 12)
    f.seek(6 * 1024 + 384)  # Block 6, offset 384
    inode = f.read(128)
    
    mode = struct.unpack('<H', inode[0:2])[0]
    uid = struct.unpack('<H', inode[2:4])[0]
    size = struct.unpack('<I', inode[4:8])[0]
    gid = struct.unpack('<H', inode[24:26])[0]
    
    print("\\nhello-world inode:")
    print(f"  Mode: 0x{mode:04x} (should be 0x81a4 = file+644)")
    print(f"  UID: {uid} (should be 1000)")
    print(f"  Size: {size} (should be 12)")
    print(f"  GID: {gid} (should be 1000)")
    
    # Test symlink
    f.seek(6 * 1024 + 512)  # Block 6, offset 512
    inode = f.read(128)
    
    mode = struct.unpack('<H', inode[0:2])[0]
    size = struct.unpack('<I', inode[4:8])[0]
    target = inode[40:51].decode('ascii')
    
    print("\\nhello symlink:")
    print(f"  Mode: 0x{mode:04x} (should be 0xa1a4 = symlink+644)")
    print(f"  Size: {size} (should be 11)")
    print(f"  Target: '{target}' (should be 'hello-world')")
