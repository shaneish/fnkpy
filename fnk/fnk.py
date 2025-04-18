from __future__ import annotations
import sys
from importlib import metadata
from typing import Any, Sequence, Iterable
from argparse import ArgumentParser, Namespace, Action
from importlib import import_module
from enum import Enum
from copy import copy
from dataclasses import dataclass


class Imports(Enum):
    variable = "VARIABLE"
    module = "MODULE"


class Status(Enum):
    VALID = 0
    ERROR = 1
    FILTER = 2


class Collection(Enum):
    SET = set
    LIST = list
    TUPLE = tuple

    @classmethod
    def infer(cls, repr: str | None) -> Collection:
        if repr:
            match repr.lower():
                case '{}' | 'set':
                    return Collection.SET
                case '()' | 'tuple':
                    return Collection.TUPLE
        return Collection.LIST


class OrderedArgsAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | bool | None = None,
        option_string: str | None = None,
    ):
        if "ordered_args" not in namespace:
            setattr(namespace, "ordered_args", [])
        previous = namespace.ordered_args
        previous.append((self.dest, values))
        setattr(namespace, "ordered_args", previous)


def parse_imports(imports: list[str] | None, import_type: Imports) -> Any:
    imported = {}
    if imports:
        for statement in imports:
            name = statement
            val = statement
            if '=' in statement:
                name, val = statement.split("=")[:2]
            if import_type == Imports.module:
                imported[name] = import_module(val)
            else:
                imported[name] = eval(val)
    return imported


def parse_args() -> Namespace:
    parser = ArgumentParser(
        prog="fnk",
        description="Small CLI tool to help you manipulate shell data with Python commands.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Show current version of fnkpy",
    )
    parser.add_argument(
        "--filter",
        "-f",
        action=OrderedArgsAction,
        type=str,
        help="Filter to apply to input stream.",
    )
    parser.add_argument(
        "--map",
        "-m",
        action=OrderedArgsAction,
        type=str,
        help="Map to apply to input stream.",
    )
    parser.add_argument(
        "--print",
        "-p",
        action=OrderedArgsAction,
        type=str,
        nargs="?",
        help="Print records for previous action"
    )
    parser.add_argument(
        "--collect",
        "-c",
        action=OrderedArgsAction,
        type=str,
        nargs='?',
        help="Collection type to collect all lines into prior to applying maps or evals"
    )
    parser.add_argument(
        "-e",
        "--expand",
        action=OrderedArgsAction,
        type=str,
        nargs="?",
        help="Flag to expand collected elements back into individual records prior to sending back to stdout/stderr"
    )
    parser.add_argument(
        "-po",
        "--pop",
        action=OrderedArgsAction,
        type=str,
        help="Place a copy of the current register into the variable namespace with specified name.  For example, using `--pop lengths` will make a copy of the current buffer with name `lengths`."
    )
    parser.add_argument(
        "-x",
        "--exec",
        action=OrderedArgsAction,
        type=str,
        help="Execute an arbitrary string of Python code with access to the namespace and buffer."
    )
    parser.add_argument(
        "--namespace-vars",
        "-n",
        type=str,
        nargs="*",
        help="Additional variables to add to execution namespace.  Should be supplied in format `--variables const_name=const_val 'extra_string=Hello there' two=2`",
    )
    parser.add_argument(
        "--repr-string",
        "-r",
        type=str,
        default="_",
        help="String to use to represent the variable in actions, default is '_'",
    )
    parser.add_argument(
        "--imports",
        "-i",
        type=str,
        nargs="*",
        help="Additional modules to import into execution namespace.  Should be supplied in format `--imports os json=js`",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Flag to display debug info"
    )
    parser.add_argument(
        "-he",
        "--hide-exceptions",
        action="store_true",
        help="Flag to hide exceptions from being directed to stdout"
    )
    parser.add_argument(
        "-sf",
        "--show-filtered",
        action="store_true",
        help="Flag to print empty lines to stdout for filtered records"
    )
    parser.add_argument(
        "-s",
        "--standardize-input",
        type=str,
        default="",
        nargs="?",
        help="Flag to pre-collect stdin into array with all input lines stripped of specified characters (default is to whitespace).  There is a slight performance cost to this due to the pre-collect phase."
    )

    parsed = parser.parse_args()
    namespace = {
        **parse_imports(parsed.imports, Imports.module),
        **parse_imports(parsed.namespace_vars, Imports.variable),
    }
    parsed.namespace = namespace
    if len(parsed.ordered_args) > 0 and parsed.ordered_args[-1] != ("print", None):
        parsed.ordered_args = parsed.ordered_args + [("print", None)]
    parsed.stages = []
    for stage in parsed.ordered_args:
        if stage[0] in ["map", "filter", "print"]:
            if parsed.stages and isinstance(parsed.stages[-1], list):
                parsed.stages[-1].append(stage)
            else:
                parsed.stages.append([stage])
        elif (len(parsed.stages) == 0 and stage[0] != "expand") or len(parsed.stages) > 0:
                parsed.stages.append(stage)
    return parsed


def evaluate(record: Any, ops: list[tuple[str, str | None]], vars: dict[str, str] | None = None, var_repr: str = "_", show_filtered: bool = False, show_exceptions: bool = False, debug: bool = False) -> Any:
    if vars is None:
        vars = {}
    act = None
    for act, fn_str in ops:
        if act != "print":
            try:
                # fn = lambda _: eval(fn_str, {"_": _, **args.namespace})
                # output = fn(record.val)
                output = eval(fn_str or var_repr, {var_repr: record, **vars})
                if debug:
                    print(f"VALID: {record = }, {output = }, {fn_str = }")
            except Exception as e: # skip excepted elements
                if show_exceptions:
                    print(f"Exception: {e}", file=sys.stderr)
                return None
            if act == "filter": # skip filtered elements or pass through previous evaluated value
                if not output:
                    if show_filtered:
                        print(f"Filtered: {record}")
                    return None
            else: # pass through valid elements that weren't filtered
                record = output
        else:
            print(record, file=sys.stdout)
    return record

def evaluate_records(collection: Iterable, ops: list[tuple[str, str | None]], args: Namespace) -> list[Any]:
    records = []
    # if args.collection:
    #     collected = args.collection.value(element.strip() for element in collection)
    #     collection = [collected]
    for record in collection:
        if isinstance(record, str):
            record = record.strip()
        # the below for-loop evaluates the output value of each input element across all maps/filters at one time
        record = evaluate(record, ops, args.namespace, args.repr_string, args.show_filtered, not args.hide_exceptions, args.debug)
        if record is not None:
            records.append(record)
    return records

def expand(record: Any, fn_str: str | None = None, vars: dict[str, Any] | None = None, var_repr: str = "_") -> list[Any]:
    if vars is None:
        vars = {}
    return [r for r in eval(fn_str or var_repr, {var_repr: record, **vars})]

def evaluate_stages(collection: Iterable, args: Namespace):
    for sub_stage in args.stages:
        if isinstance(sub_stage, list):
            collection = evaluate_records(collection, sub_stage, args)
        elif sub_stage[0] == "collect":
            # collection = collect(collection, Collection.infer(sub_stage[1]))
            collection = [Collection.infer(sub_stage[1]).value(collection)]
        elif sub_stage[0] == "expand":
            expansion = []
            for record in collection:
                expansion = expansion + expand(record, sub_stage[1], args.namespace, args.repr_string)
            collection = expansion
        elif sub_stage[0] == "pop":
            var_name = sub_stage[1].split("<-")[0].strip()
            fn = sub_stage[1].split("<-")[1].strip()
            args.namespace[var_name] = eval(fn, {args.repr_string: copy(collection), **args.namespace})
        elif sub_stage[0] == "push":
            collection = [args.namespace[sub_stage[1]]]
        elif sub_stage[0] == "exec":
            for record in collection:
                exec(sub_stage[1], {args.repr_string: record, **args.namespace})

def main():
    args = parse_args()
    if args.version:
        print(f"fnk {metadata.version('fnk')}")
    else:
        if args.debug:
            print("ARGS:", args)
        # evaluate_records(sys.stdin, args.ordered_args, args)
        collection = sys.stdin
        if args.standardize_input:
            collection = [s.strip(args.standardize_input or " \n\r\t") for s in sys.stdin.read()]
        evaluate_stages(collection, args)


if __name__ == "__main__":
    args = parse_args()
    main()


