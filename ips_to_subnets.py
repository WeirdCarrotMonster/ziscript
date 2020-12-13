#!/usr/bin/env python3

import argparse
import collections
import decimal
import functools
import ipaddress
import logging
import multiprocessing
import sys

logger = logging.getLogger("ips_to_subnets")

parser = argparse.ArgumentParser(description="Group IPs to subnets")
parser.add_argument(
    "--input",
    "-i",
    type=argparse.FileType("r"),
    default=sys.stdin,
    help="Input file (default = stdin)",
)
parser.add_argument(
    "--output",
    "-o",
    type=argparse.FileType("w"),
    default=sys.stdout,
    help="Output file (default = stdout)",
)
parser.add_argument(
    "--precision",
    "-p",
    type=float,
    default=0.5,
    help="Minimum subnet fullness (default = 0.5)",
)
parser.add_argument(
    "--filter-special",
    action="store_true",
    default=False,
    help="Filter out special subnets",
)
parser.add_argument(
    "--loglevel",
    type=str,
    default="INFO",
    choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"),
)
parser.add_argument(
    "--processes",
    type=int,
    default=multiprocessing.cpu_count(),
    help="Number of parser threads (default = cpu count)",
)
parser.add_argument("--stats", action="store_true", default=False)

args = parser.parse_args()
logging.basicConfig(level=args.loglevel)


class Node:
    __slots__ = (
        "rank",
        "child_0",
        "child_1",
        "fill",
        "parent_prefix",
        "bit_set",
        "bit_offset",
        "prefix_int",
    )

    def __init__(self, rank, parent_prefix=0, bit_set=False):
        super().__init__()
        self.rank = rank
        self.child_0 = None
        self.child_1 = None
        self.fill = 0
        self.parent_prefix = parent_prefix
        self.bit_set = bit_set

        if self.rank <= 31:
            self.bit_offset = 1 << 31 - self.rank
        else:
            self.bit_offset = 0

        if (not self.rank) or (not self.bit_set):
            self.prefix_int = 0
        else:
            self.prefix_int = 1 << (32 - self.rank)

    @property
    def current_fill(self):
        return decimal.Decimal(self.fill) / decimal.Decimal(2 ** (32 - self.rank))

    @property
    def as_network(self):
        prefix = self.prefix_int + self.parent_prefix
        return ipaddress.IPv4Network((prefix, self.rank))

    def store_address_int(self, address_int):
        if self.rank == 32:
            self.fill = 1
            return

        bit_set = bool(address_int & self.bit_offset)

        if bit_set:
            if not self.child_1:
                self.child_1 = Node(
                    self.rank + 1, self.parent_prefix + self.prefix_int, bit_set=True
                )
            self.child_1.store_address_int(address_int)
        else:
            if not self.child_0:
                self.child_0 = Node(self.rank + 1, self.parent_prefix + self.prefix_int)
            self.child_0.store_address_int(address_int)
        self.fill += 1

    def iter_subnets(self, min_fill=0, filter_special=False):
        if self.current_fill >= min_fill:
            subnet = self.as_network
            if filter_special:
                if (
                    subnet.is_multicast
                    or subnet.is_private
                    or subnet.is_reserved
                    or subnet.is_loopback
                ):
                    return
            yield subnet
            return

        if self.child_0:
            yield from self.child_0.iter_subnets(min_fill, filter_special)

        if self.child_1:
            yield from self.child_1.iter_subnets(min_fill, filter_special)


def parse_address(line):
    try:
        address = ipaddress.ip_address(line.strip())

        packed = address.packed
        return int.from_bytes(packed, "big")
    except:
        return None


root = Node(0)
pool = multiprocessing.Pool(processes=args.processes)

for address in pool.imap_unordered(parse_address, args.input, 128):
    if not address:
        continue

    root.store_address_int(address)

if args.stats:
    stats = collections.Counter()
subnet_count = 0
subnet_iter = root.iter_subnets(
    min_fill=decimal.Decimal(str(args.precision)), filter_special=args.filter_special
)

for subnet in subnet_iter:
    args.output.write(str(subnet) + "\n")
    subnet_count += 1
    if args.stats:
        stats.update((subnet.prefixlen,))

logger.debug("Merged to %s subnets", subnet_count)

if args.stats:
    logger.debug("Most common subnets:")
    for index, (prefixlen, count) in enumerate(stats.most_common(10), start=1):
        logger.debug(
            "%s) %s - %s [%s]%%",
            index,
            prefixlen,
            count,
            round(count * 100 / subnet_count, 2),
        )
