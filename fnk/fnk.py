#!/usr/bin/env python3.11
import sys
import os
from argparse import ArgumentParser
from stat import S_ISFIFO
from fnk.parser import Fn
import pkg_resources


_CMD_NAME = "fnk"
# _CMD_VERSION = pkg_resources.get_distribution(_CMD_NAME).version
_CMD_VERSION = "0.1.0"
_DEFAULT_EXPR = ""
_DEFAULT_INPUT_LINE_SEPARATOR = "\n"
_DEFAULT_OUTPUT_LINE_SEPARATOR = "\n"
if S_ISFIFO(os.fstat(0).st_mode):
    _DEFAULT_EXPR = sys.stdin.read()
else:
    if sys.platform.startswith("win"):
        _DEFAULT_INPUT_LINE_SEPARATOR = "\\n"


def main():
    parser = ArgumentParser(
        prog=_CMD_NAME,
        description="Small CLI tool to help you manipulate shell data with Python commands.",
    )
    parser.add_argument(
        "fn",
        type=str,
        default="eval",
        help="Main command you want to apply to your input. Acceptable inputs are `map`, `apply`, `agg`, `sort`, `fold`, and `filter`.",
    )
    parser.add_argument(
        "expr",
        type=str,
        nargs="?",
        default=_DEFAULT_EXPR,
        help="Expression you want evaluate using Python.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help=f"Show current version of {_CMD_NAME}",
    )
    parser.add_argument(
        "-f",
        "--function",
        type=str,
        default="|v: str| -> v",
        help="Lambda function to apply or evaluate.  Uses the following closure format: `|x: str, y: int| -> f(x, y)`. Defaults to the identity lambda.  For `fn` value of `agg`, use the name of the function which reduces a collection to a single value.",
    )
    parser.add_argument(
        "-n",
        "--no_split",
        action="store_true",
        help="Flag to not split input into multiple entries at all."
    )
    parser.add_argument(
        "-is",
        "--input_separator",
        type=str,
        default=_DEFAULT_INPUT_LINE_SEPARATOR,
        help="String to separate input data.",
    )
    parser.add_argument(
        "-os",
        "--output_separator",
        type=str,
        default=_DEFAULT_OUTPUT_LINE_SEPARATOR,
        help="String to use to join separated input data beforseparatore printing to console.",
    )
    parser.add_argument(
        "-sw",
        "--split_whitespace",
        action="store_true",
        help="Flag to override `input_separator` and split input data on all whitespace.",
    )
    parser.add_argument(
        "-s",
        "--separator",
        type=str,
        help="String to separate both input and output data.  If specified, overrides both `--input_separator` and `--output_separator`.",
    )
    parser.add_argument(
        "-se",
        "--split_entry",
        type=str,
        help="String to split data entries on if data entries are to be split.",
    )
    parser.add_argument(
        "-act",
        "--arg_container_type",
        type=type,
        default=tuple,
        help="The container type to split entries by `--split_entry` into.",
    )
    parser.add_argument(
        "-ct",
        "--container_type",
        type=str,
        default="list",
        help="Container to collect elements in.",
    )
    parser.add_argument(
        "-m",
        "--modules",
        type=str,
        nargs="*",
        help="Modules from the current Python execution environment to import before evaluating.  Calling `--module X` will import X as a module, Calling `--module X:Y` will import object Y from module X, and `--module X:Y:Z` will import object Y from module X as Z",
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        default="str",
        help="Data type to convert entries into prior to apply executing.",
    )
    parser.add_argument(
        "-rd",
        "--reduce_default",
        help="Default value to use when aggregating via reduce.",
    )
    parser.add_argument(
        "-ji",
        "--json_in",
        action="store_true",
        help="Flag to specify if input should be parsed as JSON.",
    )
    parser.add_argument(
        "-jo",
        "--json_out",
        action="store_true",
        help="Flag to specify if output should be parsed as JSON",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Flag to specify that both input and output should be parsed as JSON.",
    )
    parser.add_argument(
        "-jos",
        "--json_out_sort",
        action="store_true",
        help="Flag to specify whether output JSON will be sorted by key or not.",
    )
    parser.add_argument(
        "-joi",
        "--json_out_indent",
        type=str,
        help="Specify indentation for output JSON.",
    )
    parser.add_argument("-i", "--init", type=str, nargs="*", help="Commands to run prior to start to prep the environment and create any needed resources.")
    args = parser.parse_args()

    if (args.fn in "version") or (args.version):
        print(f"{_CMD_NAME} - v_{_CMD_VERSION}")
    else:
        # Import modules
        if args.modules is not None:
            for module in args.modules:
                split_module = module.split(":")
                match len(split_module):
                    case 1:
                        exec(f"import {module}")
                    case 2:
                        exec(f"from {split_module[0]} import {split_module[1]}")
                    case 3:
                        exec(
                            f"from {split_module[0]} import {split_module[1]} as {split_module[3]}"
                        )
        # Execute command
        Fn(args).evaluate()

if __name__ == "__main__":
    main()
