extractpart
===========

CLI utility for extracting an individual partition from MBR or GPT
disk images into a file.  eg. Extracting a partition from a VM disk image in order
to be mounted with a loopback file system (aka. "mount -o loop ...").

```sh
$ pip install git+https://github.com/mdavidsaver/extractpart#egg=extractpart
...
$ curl https://downloads.raspberrypi.org/raspbian_lite_latest > raspbian.zip
...
$ extractpart raspbian.zip info
Partition 0 offset=4.0 size=256.0 type=12 guid=
Partition 1 offset=260.0 size=1884.0 type=131 guid=
$ extractpart raspbian.zip extract 1 raspbian-part1.img
...
```

This can be mounted.

```sh
$ mkdir mntpoint
$ sudo mount -o loop raspbian-part1.img mntpoint
$ ls mntpoint
$ sudo umount mntpoint
```

Or eg. passed directly to systemd-nspawn (or similar container handling tool).

```sh
$ sudo systemd-nspawn -i raspbian-part1.img --bind=$PWD --chdir=$PWD ...
```
