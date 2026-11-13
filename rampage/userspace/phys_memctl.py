#!/usr/bin/env python3
"""Inspect and restore module-held pages by the actual test batch number."""

import argparse
import os
import sys

from physmem import Physmem, PAGE_HELD, PAGE_RELEASED, ORIGIN_SIMULATED


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/phys_mem")
    sub = parser.add_subparsers(dest="command", required=True)
    status_parser = sub.add_parser("status", help="show module-held isolation records")
    status_parser.add_argument("--run-id", type=int, required=True)
    restore_parser = sub.add_parser("restore", help="release confirmed simulated pages")
    restore_parser.add_argument("--run-id", type=int, required=True)
    restore_parser.add_argument("--simulated-only", action="store_true", required=True)
    args = parser.parse_args(argv)
    if not 0 < args.run_id < 2**64:
        parser.error("--run-id must be the actual positive batch number")

    with Physmem(args.device) as device:
        if args.command == "restore":
            result = device.restore(args.run_id)
            print(f"run={args.run_id} released={result.released} "
                  f"retained={result.retained} failed={result.failed} "
                  f"already_released={result.skipped}")
            if result.failed:
                for entry in device.entries(args.run_id):
                    if entry.state == PAGE_HELD and entry.last_error < 0:
                        print(f"PFN={entry.pfn:#x} remains held, "
                              f"errno={-entry.last_error} ({os.strerror(-entry.last_error)})")
            return 1 if result.failed else 0

        state = device.status(args.run_id)
        print(f"run={args.run_id} held={state.held} simulated={state.simulated} "
              f"unknown={state.unknown} released={state.released} "
              f"pending={state.pending} active_sessions={state.active_sessions}")
        print(f"global_pages={state.total_pages}/{state.max_total_pages} "
              f"isolation_capacity={state.max_isolated_pages} "
              f"record_capacity={state.max_isolation_records}")
        for entry in device.entries(args.run_id):
            disposition = "模块扣留" if entry.state == PAGE_HELD else "已恢复"
            origin = "软件注入已确认" if entry.origin == ORIGIN_SIMULATED else "来源不明"
            print(f"{disposition} run={entry.run_id} session={entry.session_id} "
                  f"index={entry.index} PFN={entry.pfn:#x} "
                  f"type={entry.error_type} offset={entry.byte_offset} "
                  f"origin={origin} map_refs={entry.map_refs} "
                  f"module_refs={entry.module_refs} page_refcount={entry.page_refcount} "
                  f"last_error={entry.last_error}")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as exc:
        print(f"phys_memctl: {exc}", file=sys.stderr)
        sys.exit(1)
