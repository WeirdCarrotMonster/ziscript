#!/usr/bin/env python3

import argparse
import glob
import itertools
import sys
import ipaddress
import logging
import multiprocessing


logger = logging.getLogger(__file__)


parser = argparse.ArgumentParser(description="Extract IPs from zapret-info csv dumps")
parser.add_argument("sources", type=str, nargs="+", help="Source files glob")
parser.add_argument(
    "--output",
    "-o",
    type=argparse.FileType("w"),
    default=sys.stdout,
    help="Output file (default = stdout)",
)
parser.add_argument(
    "--processes",
    type=int,
    default=multiprocessing.cpu_count(),
    help="Number of parser threads (default = cpu count)",
)
parser.add_argument(
    "--chunksize", type=int, default=128, help="Parser chunksize (default = 128)"
)
parser.add_argument(
    "--loglevel",
    type=str,
    default="INFO",
    choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"),
)

args = parser.parse_args()


logging.basicConfig(level=args.loglevel.upper())

dest = args.output

source_files = sorted(
    set(itertools.chain.from_iterable(glob.glob(_) for _ in args.sources))
)

if not source_files:
    sys.exit("No sources specified")


def file_iterator():
    for source_file in source_files:
        logger.debug("Processing file %s", source_file)
        with open(source_file, "r", encoding="cp1251") as src:
            yield from src


def handle_line(line):
    if ";" not in line:
        return []

    ip_entries, _ = line.split(";", 1)
    line_ips = []
    for entry in ip_entries.split("|"):
        entry = entry.strip()
        try:
            address = ipaddress.ip_address(entry)
            if address.version == 4:
                line_ips.append(address)
        except ValueError:
            try:
                network = ipaddress.ip_network(entry)
                if network.version == 4:
                    line_ips.extend(network.hosts())
            except ValueError:
                continue
    return line_ips


ips = set()
pool = multiprocessing.Pool(processes=args.processes)

for line_ips in pool.imap_unordered(handle_line, file_iterator(), args.chunksize):
    for address in line_ips:
        if address not in ips:
            ips.add(address)
            dest.write(str(address) + "\n")
