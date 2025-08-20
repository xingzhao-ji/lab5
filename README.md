# Hey! I'm Filing Here

In this lab, I successfully implemented a 1 MiB ext2 filesystem with 2 directories, 1 regular file, and 1 symbolic link.

## Building
Run this command in the same directory where the Makefile is located to build:
```shell
make
```

## Running
Create the filesystem image with ./ext2-create, then verify it with dumpe2fs and fsck.ext2:
```shell
./ext2-create
dumpe2fs cs111-base.img
fsck.ext2 cs111-base.img
```
Mount the filesystem to explore its contents:
```shell
mkdir mnt
sudo mount -o loop cs111-base.img mnt
ls -la mnt/
sudo umount mnt
rmdir mnt
```

## Cleaning up
To clean up and remove the executables created, use this command:
```shell
make clean
```
