#!/bin/sh
set -e -x

# assume non-privlaged user
PATH=$PATH:/sbin:/usr/sbin

# Create some empty test images to play around with

rm -f mbr.img mbrext.img gpt.img
dd if=/dev/zero of=mbr.img bs=1048576 count=10
dd if=/dev/zero of=mbrext.img bs=1048576 count=10
dd if=/dev/zero of=gpt.img bs=1048576 count=10

# cf. "man sfdisk"  INPUT FORMATS
# note that cfdisk can output a script file to replicate a given image

# Create Fat32 and Linux partitions
cat <<EOF | sfdisk ./mbr.img
label: dos
size=5MiB, type=b, bootable
type=83
EOF

# calculated from fdisk -l output
# offset is in bytes, Start * 512
# size is kb (2**10).  blocks/2
mke2fs -F -E offset=6291456 ./mbr.img 4096k

# Create extended Fat32 and Linux partitions
cat <<EOF | sfdisk ./mbrext.img
label: dos
size=1MiB, type=b, bootable
size=1MiB, type=82
size=1MiB, type=83
type=5
size=1MiB, type=83
type=83
EOF

mke2fs -F -E offset=3145728 ./mbrext.img 1024
mke2fs -F -E offset=5242880 ./mbrext.img 1024
mke2fs -F -E offset=7340032 ./mbrext.img 3072

# Create a EFI system and Linux partitions
cat <<EOF | sfdisk ./gpt.img
label: gpt
size=5MiB, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, bootable
type=0FC63DAF-8483-4772-8E79-3D69D8477DE4
EOF

mke2fs -F -E offset=6291456 ./gpt.img 3072
