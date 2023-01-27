#!/usr/bin/env python3.11
import sys
import os
import json
from typing import Any, Callable
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
        self.parsed_expr = self._parse_expr()

    def evaluate(self):
        match self.args.fn:
            case "map":
                self.map()
            case "filter":
                self.filter()
            case "apply" | "exec":
                self.apply()
            case "agg" | "aggregate":
                self.agg()
            case "fold" | "reduce":
                self.fold()
            case "filtermap" | "fmap" | "filter_map" | "eval":
                self.filter_map()
            case "sort":
                self.sort()
            case _:
                print("Not a supported function class.")

    def map(self):
        output_collection = self.args.container_type(
            map(self.args.func, self.parsed_expr)
        )
        self._stdout(output_collection)

    def filter(self):
        output_collection = self.args.container_type(
            filter(self.args.func, self.parsed_expr)
        )
        self._stdout(output_collection)

    def filter_map(self):
        output_collection = self.args.container_type(
            filter(
                lambda entry: entry not in [None, "", set(), list(), dict(), tuple()],
                map(self.args.func, self.parsed_expr),
            )
        )
        self._stdout(output_collection)

    def apply(self):
        for entry in self.parsed_expr:
            cmd = self.args.func(entry)
            exec(cmd)

    def sort(self):
        if self.args.func == "reverse":
            output_collection = self.args.container_type(
                sorted(self.parsed_expr), reverse=True
            )
        else:
            output_collection = self.args.container_type(
                sorted(self.parsed_expr), key=self.args.func
            )
        self._stdout(output_collection)

    def agg(self):
        out = ""
        match self.args.function:
            case "concat":
                out = "".join([str(entry) for entry in self.parsed_expr])
            case "stats":
                out = [
                    f"Mean   -> {mean(self.parsed_expr)}",
                    f"Median -> {median(self.parsed_expr)}",
                    f"Mode   -> {mode(self.parsed_expr)}",
                    f"Stdev  -> {stdev(self.parsed_expr)}",
                    f"Var    -> {variance(self.parsed_expr)}",
                ]
            case "sum":
                out = sum([entry for entry in self.parsed_expr])
            case "any":
                out = any([self._try_eval(eval, entry) for entry in self.parsed_expr])
            case "all":
                out = all([self._try_eval(eval, entry) for entry in self.parsed_expr])
            case "product":
                out = reduce(lambda a, b: a * b, self.parsed_expr, 1)
            case other:
                out = eval(f"{other}({self.parsed_expr})")
        self._stdout(out)

    def fold(self):
        if self.args.reduce_default is None:
            out = reduce(self.args.func, self.parsed_expr)
        else:
            out = reduce(self.args.func, self.parsed_expr, self.args.reduce_default)
        self._stdout(out)

    def _try_eval(
        self,
        fn: Callable,
        entry: str | list | tuple | dict | set,
        default: str | None = None,
        distribute=False,
        positional=True,
    ) -> Any:
        out = default
        try:
            if not distribute:
                out = fn(entry)
            elif positional:
                out = fn(*entry)
            else:
                out = fn(**entry)
        except:
            pass
        return out

    def _try_exec_dist_vars(
        self, fn: Callable, entry: str | int | float | bool | list | set | dict | tuple
    ) -> str:
        cmd = str(self._try_eval(fn, entry, ""))
        if self.args.distribute_args:
            if self.args.arg_container_type in [list, tuplmape]:
                cmd = str(self._try_eval(fn, entry, "", True))
            elif self.args.arg_container_type in [dict]:
                cmd = str(self._try_eval(fn, entry, "", True, False))
        return cmd

    def _try_eval_dist_vars(
        self, fn: Callable, entry: str | int | float | bool | list | set | dict | tuple
    ) -> Any:
        cmd = self._try_eval(fn, entry)
        if self.args.distribute_args:
            if self.args.arg_container_type in [list, tuple]:
                cmd = self._try_eval(fn, entry, None, True)
            elif self.args.arg_container_type in [dict]:
                cmd = self._try_eval(fn, entry, None, True, False)
        return cmd

    def _parse_expr(self) -> set | list | dict | tuple:
        if self.args.json_in:
            input_json = json.loads(self.args.expr)
            if type(input_json) == list:
                return input_json
            else:
                return [item for item in input_json.items()]
        if self.args.split_whitespace:
            the_iterable = self.args.expr.split()
        else:
            the_iterable = self.args.expr.split(self.args.input_separator)

        if not self.args.split_entry:
            return self.args.container_type(
                [self._try_eval(self.args.type, entry) for entry in the_iterable]
            )
        else:
            return self.args.container_type(
                [
                    self.args.arg_container_type(
                        map(
                            lambda element: self._try_eval(self.args.type, element),
                            entry.split(self.args.entry_separator),
                        )
                    )
                    for entry in the_iterable
                ]
            )

    def _stdout(self, output: str | int | float | bool | set | list | dict | tuple):
        out = ""
        if self.args.json_out:
            out_json = None
            try:
                out_json = dict(output)
            except:
                try:
                    out_json = list(output)
                except:
                    out = "Output cannot be parsed as JSON."
            if out_json is not None:
                out = json.dumps(
                    out_json,
                    indent=self.args.json_out_indent,
                    sort_keys=self.args.json_out_sort,
                )
        elif type(output) in [set, list, dict, tuple]:
            out = self.args.output_separator.join([str(entry) for entry in output])
        elif type(output) in [int, float, bool]:
            out = str(output)
        print(out)

    def _adjust_args(self, args: Namespace) -> Namespace:
        lambda_vars = (
            args.function.split("->")[0]
            .replace(" ", "")
            .replace("|", "")
            .replace("(", "")
            .replace(")", "")
            .strip()
        )
        lambda_func = "->".join(args.function.split("->")[1:]).strip()
        if len(args.function.split("->")) == 1:
            if args.function in ["sum", "product", "stats"]:
                args.type = "int" if (args.type == "int") else "float"
            args.func = lambda v: v
        elif args.fn == "eval":
            args.func = lambda s: eval(s)
        elif args.fn == "apply":
            args.func = lambda entry: self._try_exec_dist_vars(
                eval(f"lambda {lambda_vars}: {lambda_func}"), entry
            )
        else:
            args.func = lambda entry: self._try_eval_dist_vars(
                eval(f"lambda {lambda_vars}: {lambda_func}"), entry
            )
        args.expr = args.expr.strip()
        if args.separator is not None:
            args.input_separator = args.separator
            args.output_separator = args.separator
        args.container_type = eval(args.container_type)
        args.type = eval(args.type)
        if (args.json_out_indent is not None) and (args.json_out_indent.isdigit()):
            args.json_out_indent = int(args.json_out_indent)
        if args.json:
            args.json_in = True
            args.json_out = True
        return args


if __name__ == "__main__":
    parser = ArgumentParser(
        prog=_CMD_NAME,
        description="Small CLI tool to help you manipulate shell data with Python commands.",
    )
    parser.add_argument(
        "fn",
        type=str,
        nargs="?",
        default="eval",
        help="Main command you want to apply to your input. Acceptable inputs are `map`, `apply`, and `filter`.",
    )
    parser.add_argument(
        "-x",
        "--expr",
        type=str,
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
        default="|v| -> v",
        help="Lambda function to apply or evaluate.  Uses the following closure format: `|x, y| -> f(x, y)`.",
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
        action="store_true",
        help="Flag to split each entry being iterated over into it's own container.",
    )
    parser.add_argument(
        "-es",
        "--entry_separator",
        type=str,
        default=" ",
        help="String to split data entries on.",
    )
    parser.add_argument(
        "-da",
        "--distribute_args",
        action="store_true",
        help="If present, treat collections generated by inner separation as arguments to function in `--function`.",
    )
    parser.add_argument(
        "-act",
        "--arg_container_type",
        type=type,
        default=tuple,
        help="The container type to split entries by `--entry_separator` into.",
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
        "--module",
        type=str,
        nargs="*",
        help="Module from the current Python execution environment to import before evaluating.  Calling `--module X` will import X as a module, Calling `--module X:Y` will import object Y from module X, and `--module X:Y:Z` will import object Y from module X as Z",
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
        type=Any,
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
    args = parser.parse_args()

    if (args.fn in "version") or (args.version):
        print(f"{_CMD_NAME} - v_{_CMD_VERSION}")
    else:
        for module in args.module:
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
        Fn(args).evaluate()
