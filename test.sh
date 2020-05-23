#!/bin/sh
set -e -x

[ "$PYTHON" ] || PYTHON=python

# assume non-privlaged user
PATH=$PATH:/sbin:/usr/sbin

ep() {
    $PYTHON -m extractpart "$@"
}

trap 'rm -f temp.img' TERM INT QUIT EXIT

echo "============ mbr.img =============="
ep -u b mbr.img info

ep -u b mbr.img extract 1 temp.img
e2fsck -nf temp.img

echo "============ mbrext.img =============="
ep -u b mbrext.img info

ep -u b mbrext.img extract 2 temp.img
e2fsck -nf temp.img

ep -u b mbrext.img extract 3.0 temp.img
e2fsck -nf temp.img

ep -u b mbrext.img extract 3.1 temp.img
e2fsck -nf temp.img

echo "============ gpt.img =============="
ep -u b gpt.img info

ep -u b gpt.img extract 1 temp.img
e2fsck -nf temp.img
