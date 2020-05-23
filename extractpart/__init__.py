"""Extract individual partitions from MBR or GUID/GPT disk image

https://en.wikipedia.org/wiki/Master_boot_record

https://en.wikipedia.org/wiki/Extended_boot_record

https://en.wikipedia.org/wiki/GUID_Partition_Table
"""

import sys
import re
import struct
import zipfile
import logging
from collections import OrderedDict

_log = logging.getLogger(__name__)

if sys.version_info<(3,0):
    sys.stderr.write('py3 required\n')
    sys.exit(5)

def decode_guid(raw):
    # GUIDs are encoded is 16 bytes of wonderly mixed-endian
    # LLLLLLLL-LLLL-LLLL-BBBB-BBBBBBBBBBBB
    A, B, C = struct.unpack('<IHH', raw[:8])
    DE, = struct.unpack('>Q', raw[8:16])
    D, E = DE>>48, DE&0xffffffffffff
    parts = []
    for P,n in zip([A,B,C,D,E], (8,4,4,4,12)):
        fmt = '{:0%dX}'%n
        parts.append(fmt.format(P))
    return '-'.join(parts)
    
    return ''.join(['{:02X}'.format(b) for b in B])

class Image(object):
    def __init__(self, image):
        self.image = image
        self.IMG = None
        self._clean = []
        self.gpt = False
        self.table = self.guids = None

    def readexactly(self, N, at=None):
        if at is not None:
            self.IMG.seek(at)
        B = self.IMG.read(N)
        if len(B)<N:
            raise RuntimeError('Truncated image')
        return B

    def __enter__(self):
        if self.image.endswith('.zip'):
            _log.debug('Open ZIP: %s', self.image)
            ZIP = zipfile.ZipFile(self.image, 'r')
            for zname in ZIP.namelist():
                if zname.endswith('.img'):
                    _log.debug('Using: %s', zname)
                    self.IMG = ZIP.open(zname, 'r') # 'b' implied?
                    self._clean = [self.IMG.close, ZIP.close]
                    break
            else:
                raise RuntimeError('.zip contains no .img')

        else:
            _log.debug('Open RAW: %s', self.image)
            self.IMG = open(self.image, 'rb')
            self._clean = [self.IMG.close]

        # read MBR record
        self.MBR = self.readexactly(512, at=0)

        # basic (in)sanity checks
        if self.MBR[-2:]!=b'\x55\xaa':
            raise RuntimeError('Corrupt MBR[510:512]={}'.format(repr(self.MBR)))

        # is this really GPT?
        p0type = self.MBR[446+4]
        if p0type==0xee:
            _log.debug('maybe GPT')
            self.GPT = self.readexactly(92, at=512)
            if self.GPT[:8]==b'EFI PART':
                _log.debug('found GPT')
                self.gpt = True

        self.table = OrderedDict()
        self.guids = {}

        if self.gpt:
            _log.debug('read GPT partitions')

            lstart, lcnt, lsize = struct.unpack('<QII', self.GPT[72:88])
            lstart *= 512
            if lsize<128:
                _log.warn('GPT partition info size %s < 128', lsize)

            for i in range(lcnt):
                part = self.readexactly(lsize, at=lstart + i*lsize)
                ptype = decode_guid(part[0:16])
                if ptype=='00000000-0000-0000-0000-000000000000':
                    continue
                offset, last = struct.unpack('<QQ', part[32:48])
                size = 1+last-offset

                name = str(i)
                self.table[name] = entry = {
                    'name': name,
                    'type': str(ptype),
                    'offset': offset*512,
                    'size': size*512,
                    'guid':decode_guid(part[0:16]),
                }
                self.guids[entry['guid']] = name
                _log.debug('Add %s', entry)

        else:
            _log.debug('read MBR partitions')
            for i,off in enumerate(range(446, 495, 16)):
                part = self.MBR[off:(off+16)]
                ptype = part[4]
                sector0, = struct.unpack('<I', part[8:12])
                sectorcnt, = struct.unpack('<I', part[12:16])

                offset = sector0*512 # sectors to bytes
                size   = sectorcnt*512

                if ptype==0:
                    continue

                name = str(i)
                self.table[name] = entry = {
                    'name': str(i),
                    'type': str(ptype),
                    'offset': offset,
                    'size': size,
                    'guid': '',
                }
                _log.debug('Add %s', entry)

                if ptype in (5, 7):
                    _log.debug('Process Extended %d', i)

                    # Extended partition(s) are effectively a linked list.
                    # Nodes have the same format as an MBR with only one or two
                    # entries used. (actual partition, and maybe next node)

                    eoffset, esize = offset, size
                    j=0
                    done=False
                    while not done:
                        self.IMG.seek(eoffset)
                        _log.debug('Read EMBR @%d', eoffset)

                        EMBR = self.readexactly(512, at=eoffset)
                        if EMBR[-2:]!=b'\x55\xaa':
                            _log.error('Ignore corrupt extended partition %s', i)
                            break

                        for off in range(446, 463, 16):
                            part = EMBR[off:(off+16)]
                            ptype = part[4]
                            sector0, = struct.unpack('<I', part[8:12])
                            sectorcnt, = struct.unpack('<I', part[12:16])

                            offset = sector0*512 # sectors to bytes
                            size   = sectorcnt*512

                            _log.debug('Read EMBR @%d+%d type=%d offset=%d size=%d', eoffset, off, ptype, offset, size)

                            if ptype==0:
                                done = True
                                break
                            elif ptype in (5, 7):
                                eoffset += offset
                                break

                            name = '{}.{}'.format(i,j)
                            j += 1
                            self.table[name] = entry = {
                                'name': name,
                                'type': str(ptype),
                                'offset': eoffset+offset,
                                'size': size,
                                'guid': '',
                            }
                            _log.debug('Add %s', entry)

        return self

    def __exit__(self,A,B,C):
        clean, self._clean = self._clean, []
        for C in clean:
            C()

def info(img, args):
    for ent in img.table.values():
        ent['uoffset'] = args.unit(ent['offset'])
        ent['usize'] = args.unit(ent['size'])
        print('Partition {name} offset={uoffset} size={usize} type={type} guid={guid}'.format(**ent))

def extract(img, args):
    pname = img.guids.get(args.partition) or args.partition
    entry = img.table[pname]
    _log.info('Extracting partition %s', pname)

    img.IMG.seek(entry['offset'])

    i, N = 0, entry['size']
    while i<N:
        B = img.IMG.read(16*2**20)
        if len(B)==0:
            break
        args.output.write(B)
        i += len(B)
        _log.info('%d/%d', i, N)
        

def getargs():
    from argparse import ArgumentParser, FileType
    P = ArgumentParser()
    P.add_argument('image', help='MBR or GUID disk image file.  May be .zip')
    P.add_argument('-v', '--verbose', action='store_const', const=logging.DEBUG, default=logging.INFO,
                   dest='level')

    def units(s):
        return {
            'S': lambda s:s/512.,
            'B': lambda s:s,
            'K': lambda s:s/2.0**10,
            'M': lambda s:s/2.0**20,
            'G': lambda s:s/2.0**30,
        }[s.upper()]
    P.add_argument('-u', '--unit', type=units, default=units('M'))

    SP = P.add_subparsers()

    S = SP.add_parser('info', help='Print partition table info')
    S.set_defaults(action=info)

    S = SP.add_parser('extract', help='Extract partition to file (or - for stdout)')
    S.add_argument('partition', help='Partition # or GUID')
    S.add_argument('output', type=FileType('wb'))
    S.set_defaults(action=extract)

    return P

def main():
    args = getargs().parse_args()
    logging.basicConfig(level=args.level)
    with Image(args.image) as img:
        args.action(img, args)
