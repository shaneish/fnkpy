#! usr/bin/env python3.11

import sys
import os
from typing import Union, Literal
from argparse import ArgumentParser, Namespace
from stat import S_ISFIFO


_CMD_NAME = "fn"
default_data = ""
default_line_separator = "\n"
if S_ISFIFO(os.fstat(0).st_mode):
    default_expr = sys.stdin.read()
if sys.platform.startswith("win"):
    default_line_separator = "\\n"

class Fn:

    def __init__(self, args: Namespace):
        self.args = self._adjust_args(args)
        self._load_imports(args.import)

    def _adjust_args(args: Namespace) -> Namespace:
        lambda_vars = args.function.split("->")[0].replace(" ", "").replace("|", "").strip()
        lambda_func = "->".join(args.function.split("->")[1:]).strip()
        args.function = f"lambda {lambda_vars}: {lambda_func}"
        if args.agg_default is None:
            match args.data_type:
                case "str":
                    args.agg_default = ""
                case "int":
                    args.agg_default = 0
                case "float":
                    args.agg_default = 0
                case "list":
                    args.agg_default = []
                case "set":
                    args.agg_default = set()
                case "dict":
                    args.agg_default = dict()
                case "tuple":
                    args.agg_default = tuple()
        args.collection_type = eval(args.collection_type)
        args.data_type = eval(args.data_type)
        return args
if __name__ == "__main__":
    parser = ArgumentParser(prog = _CMD_NAME, description = "Small CLI tool to help you manipulate shell data with Python commands.")
    parser.add_argument("fn", type = str, help = "Main command you want to apply to your input. Acceptable inputs are `map`, `apply`, and `filter`.")
    parser.add_argument("expr", type = str, default = default_data, help = "Expression you want evaluate using Python.")
    parser.add_argument("-f", "--function", type = str, default = "|__v__| -> __v__", help = "Lambda function to apply or evaluate.  Uses the following closure format: `|x, y| -> f(x, y)`.")
    parser.add_argument("-si", "--separator_in", type = str, default = default_line_separator, help = "String to separate input data.")
    parser.add_argument("-so", "--separator_out", type = str, default = "\n", help = "String to use to join separated input data before printing to console.")
    parser.add_argument("-sw", "--separator_whitespace", action = "store_true", help = "Flag to override `separator_in` and split input data on all whitespace.")
    parser.add_argument("-c", "--collection_type", type = Literal["set", "list", "dict", "tuple"], default = "list", help = "Container to collect elements in.")
    parser.add_argument("-i", "--import", type = str, action = "append", help = "Module from the current Python execution environment to import before evaluating.")
    parser.add_argument("-d", "--data_type", type = Literal["str", "int", "float", "list", "set", "dict", "tuple"], default = "str", help = "Data type to convert entries into prior to apply executing.")
    parser.add_argument("-a", "--agg_default", type = Optional[str], default = None, help = "Default value to use when aggregating via reduce.")
