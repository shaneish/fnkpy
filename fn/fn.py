#!/usr/bin/env python3.11

import sys
import os
from typing import Literal, Any
from argparse import ArgumentParser, Namespace
from stat import S_ISFIFO
from statistics import mean, median, mode, stdev, variance
from functools import reduce


_CMD_NAME = "fn"
_CMD_VERSION = "0.1.0"
_DEFAULT_EXPR = ""
_DEFAULT_INPUT_LINE_SEPARATOR = "\n"
_DEFAULT_OUTPUT_LINE_SEPARATOR = "\n"
if S_ISFIFO(os.fstat(0).st_mode):
    _DEFAULT_EXPR = sys.stdin.read()
else:
    if sys.platform.startswith("win"):
        _DEFAULT_INPUT_LINE_SEPARATOR = "\\n"

class Fn:

    def __init__(self, args: Namespace):
        self.args = self._adjust_args(args)
        self._load_imports()
        self.parsed_expr = self._parse_expr()

    def evaluate(self):
        match self.args.fn:
            case "map":
                self.map()
            case "filter":
                self.filter()
            case "apply":
                self.apply()
            case "agg":
                self.agg()
            case "fold":
                self.fold()
            case _:
                print("Not a supported function class.")

    def map(self):
        output_collection = self.args.collection_type(map(self.args.func, self.parsed_expr))
        self._stdout(output_collection)

    def filter(self):
        output_collection = self.args.collection_type(filter(self.args.func, self.parsed_expr))
        self._stdout(output_collection)

    def apply(self):
        for entry in self.parsed_expr:
            exec(str(self.args.function(entry)))

    def agg(self):
        out = ""
        match self.args.function:
            # case "sum":
            #     out = sum(self.parsed_expr)
            case "concat":
                out = "".join([str(entry) for entry in self.parsed_expr])
            # case "any":
            #     out = any(self.parsed_expr)
            # case "all":
            #     out = all(self.parsed_expr)
            case "stats":
                out = [
                        f"Mean   -> {mean(self.parsed_expr)}",
                        f"Median -> {median(self.parsed_expr)}",
                        f"Mode   -> {mode(self.parsed_expr)}",
                        f"Stdev  -> {stdev(self.parsed_expr)}",
                        f"Var    -> {variance(self.parsed_expr)}"
                ]
            case other:
                out = eval(f"{other}({self.parsed_expr})")
        self._stdout(out)

    def fold(self):
        if self.args.reduce_default is None:
            out = reduce(self.args.func, self.parsed_expr)
        else:
            out = reduce(self.args.func, self.parsed_expr, self.args.reduce_default)
        self._stdout(out)

    def _parse_expr(self) -> set | list | dict | tuple:
        if self.args.separator_whitespace:
            the_iterable = self.args.expr.split()
        else:
            the_iterable = self.args.expr.split(self.args.separator_in)

        return self.args.collection_type([self.args.data_type(entry) for entry in the_iterable])

    def _stdout(self, output: str | int | float | bool | set | list | dict | tuple):
        out = ""
        if type(output) in [set, list, dict, tuple]:
            out = self.args.separator_out.join([str(entry) for entry in output])
        elif type(output) in [int, float, bool]:
            out = str(output)
        print(out)

    def _load_imports(self):
        for module in self.args.module:
            exec(f"import {module}")

    def _adjust_args(self, args: Namespace) -> Namespace:
        if args.module is None:
            args.module = []
        lambda_vars = args.function.split("->")[0].replace(" ", "").replace("|", "").strip()
        lambda_func = "->".join(args.function.split("->")[1:]).strip()
        args.func = eval(f"lambda {lambda_vars}: {lambda_func}") if (len(args.function.split("->")) > 1) else lambda v: v
        args.expr = args.expr.strip()
        if args.separator is not None:
            args.separator_in = args.separator
            args.separator_out = args.separator
        args.collection_type = eval(args.collection_type)
        args.data_type = eval(args.data_type)
        return args


if __name__ == "__main__":
    parser = ArgumentParser(prog = _CMD_NAME, description = "Small CLI tool to help you manipulate shell data with Python commands.")
    parser.add_argument("fn", type = str, help = "Main command you want to apply to your input. Acceptable inputs are `map`, `apply`, and `filter`.")
    parser.add_argument("-x", "--expr", type = str, default = _DEFAULT_EXPR, help = "Expression you want evaluate using Python.")
    parser.add_argument("-v", "--version", action = "store_true", help = f"Show current version of {_CMD_NAME}")
    parser.add_argument("-f", "--function", type = str, default = "|v| -> v", help = "Lambda function to apply or evaluate.  Uses the following closure format: `|x, y| -> f(x, y)`.")
    parser.add_argument("-si", "--separator_in", type = str, default = _DEFAULT_INPUT_LINE_SEPARATOR, help = "String to separate input data.")
    parser.add_argument("-so", "--separator_out", type = str, default = _DEFAULT_OUTPUT_LINE_SEPARATOR, help = "String to use to join separated input data before printing to console.")
    parser.add_argument("-sw", "--separator_whitespace", action = "store_true", help = "Flag to override `separator_in` and split input data on all whitespace.")
    parser.add_argument("-s", "--separator", type = str, default = None, help = "String to separate both input and output data.  If specified, overrides both `--separator_in` and `--separator_out`.")
    parser.add_argument("-c", "--collection_type", type = str, default = "list", help = "Container to collect elements in.")
    parser.add_argument("-m", "--module", type = str, action = "append", help = "Module from the current Python execution environment to import before evaluating.")
    parser.add_argument("-d", "--data_type", type = str, default = "str", help = "Data type to convert entries into prior to apply executing.")
    parser.add_argument("-r", "--reduce_default", type = Any, default = None, help = "Default value to use when aggregating via reduce.")
    args = parser.parse_args()

    if args.fn in ["version", "v", "--version", "-v"]:
        print(f"{_CMD_NAME} version-{_CMD_VERSION}")
    else:
        Fn(args).evaluate()
