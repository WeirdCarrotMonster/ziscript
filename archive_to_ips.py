#!/usr/bin/env python3

import argparse
import ipaddress
import logging
import multiprocessing
import re
import sys
import zipfile

EXPRESSION = re.compile(".*dump.*\.csv")
LOGGER = logging.getLogger("archive_to_ips")


parser = argparse.ArgumentParser(description="Extract IPs from zapret-info archive")
parser.add_argument(
    "archive", type=argparse.FileType("rb"), default=sys.stdin, help="Source archive"
)
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


def file_iterator():
    archive = zipfile.ZipFile(args.archive)

    for filename in archive.namelist():
        if EXPRESSION.match(filename):
            LOGGER.debug("Processing file %s", filename)
            with archive.open(filename, "r") as src:
                yield from src


def handle_line(line):
    line = line.decode("cp1251")

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
