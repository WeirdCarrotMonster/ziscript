#!/usr/bin/env python3

import argparse
import contextlib
import logging
import os
import pathlib
import shutil
import tempfile
import urllib.error
import urllib.request

LOGGER = logging.getLogger("get_archive")
ARCHIVE_SOURCE = "https://github.com/zapret-info/z-i/archive/master.zip"


def get_parser():
    parser = argparse.ArgumentParser(description="Download zapret-info archive")
    parser.add_argument("--cache", type=str, help="Cache directory")
    parser.add_argument(
        "--print", default=False, action="store_true", help="Print archive path"
    )
    parser.add_argument(
        "--loglevel",
        type=str,
        default="INFO",
        choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"),
    )
    return parser


def get_cache_dir(cache_path: str = None):
    if cache_path:
        cache_dir = pathlib.Path(cache_path)
    elif xdg_cache_dir := os.environ.get("XDG_CACHE_DIR"):
        cache_dir = pathlib.Path(xdg_cache_dir) / "ziscript"
    elif home_dir := os.environ.get("HOME"):
        cache_dir = pathlib.Path(home_dir) / ".cache" / "ziscript"
    else:
        raise Exception("Can't find suitable cache directory")

    LOGGER.debug("Using '%s' for cache", cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    return cache_dir


def get_etag(etag_path) -> bytes:
    with contextlib.suppress(Exception):
        with open(etag_path, "r") as etag_file:
            return etag_file.read().strip()


def set_etag(etag_path, value):
    with open(etag_path, "w") as etag_file:
        etag_file.write(value)


def download_archive(cache_path: str = None):
    cache_dir = get_cache_dir(cache_path)

    archive_file_path = pathlib.Path(cache_dir) / "master.zip"
    etag_file_path = pathlib.Path(cache_dir) / "etag"
    etag = get_etag(etag_file_path)

    headers = {}
    if etag:
        headers["If-None-Match"] = etag

    request = urllib.request.Request(ARCHIVE_SOURCE, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            with open(archive_file_path, "wb") as archive_file:
                shutil.copyfileobj(response, archive_file)
        etag_value = response.getheader("ETag")
        set_etag(etag_file_path, etag_value)
    except urllib.error.HTTPError as response_error:
        if response_error.code != 304:
            raise
        LOGGER.info("Cached file not modified")

    return archive_file_path


def main():
    parser = get_parser()
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel.upper())

    stored_file = download_archive(args.cache)

    if args.print:
        print(stored_file)


if __name__ == "__main__":
    main()
