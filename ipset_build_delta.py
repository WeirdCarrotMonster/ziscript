#!/usr/bin/env python3

import argparse
import sys
import logging

logger = logging.getLogger(__file__)

parser = argparse.ArgumentParser(description="Generate ipset update commands")
parser.add_argument("ipset", type=str, help="Ipset name")
parser.add_argument(
    "--new",
    type=argparse.FileType("r"),
    default=sys.stdin,
    help="New IPs for ipset source (default = stdin)",
)
parser.add_argument(
    "--old", type=argparse.FileType("r"), help="Old ipset state file in plain format"
)
parser.add_argument(
    "--output",
    "-o",
    type=argparse.FileType("w"),
    default=sys.stdout,
    help="Delta output file (default = stdout)",
)
parser.add_argument(
    "--loglevel",
    type=str,
    default="INFO",
    choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"),
)

args = parser.parse_args()
logging.basicConfig(level=args.loglevel)


def parse_ip_subnet(value):
    if any(c.isalpha() for c in value):
        return

    return value.strip()


old_subnet_iter = filter(None, map(parse_ip_subnet, args.old or []))
new_subnet_iter = filter(None, map(parse_ip_subnet, args.new or []))

old_subnets = set(old_subnet_iter)
new_subnets = set(new_subnet_iter)

removed_subnets = old_subnets.difference(new_subnets)
added_subnets = new_subnets.difference(old_subnets)

logger.debug("Removed %s subnets", len(removed_subnets))
logger.debug("Added %s subnets", len(added_subnets))

for removed_subnet in removed_subnets:
    args.output.write("del " + args.ipset + " " + str(removed_subnet) + "\n")


for added_subnet in added_subnets:
    args.output.write("add " + args.ipset + " " + str(added_subnet) + "\n")
