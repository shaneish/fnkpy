import sys
import io
from typing import Any, Sequence, Self, Callable
from argparse import ArgumentParser, Namespace, Action
from importlib import import_module
from enum import Enum
from dataclasses import dataclass


CMD_NAME = "fnk"


class Imports(Enum):
    variable = "VARIABLE"
    module = "MODULE"


class ActionType(Enum):
    map = "MAP"
    filter = "FILTER"

    @classmethod
    def from_str(cls, s: str) -> Self:
        return eval(f"ActionType.{s}")


class Status(Enum):
    VALID = 0
    ERROR = 1
    FILTER = 2


@dataclass
class Record:
    init: str
    val: str
    status: Status
    desc: str | None = None


class OrderedArgsAction(Action):
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[str] | None,
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


def parse_actions(actions: list[tuple[str, str]], namespace: dict[str, Any] | None = None) -> list[Function]:
    if not namespace:
        namespace = {}
    action_steps = []
    for action_type, fn_def in actions:
        action_steps.append(Function(ActionType.from_str(action_type), lambda _: eval(fn_def, namespace)))
    return action_steps


def parse_args() -> Namespace:
    parser = ArgumentParser(
        prog=CMD_NAME,
        description="Small CLI tool to help you manipulate shell data with Python commands.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help=f"Show current version of {CMD_NAME}",
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
        "--vars",
        "-V",
        type=str,
        nargs="*",
        help="Additional variables to add to execution namespace.  Should be supplied in format `--variables var_name=var_val 'extra_string=Hello there' two=2`",
    )
    parser.add_argument(
        "--imports",
        "-i",
        type=str,
        nargs="*",
        help="Additional modules to import into execution namespace.  Should be supplied in format `--imports os json=js`",
    )
    parser.add_argument(
        "-s",
        "--show-filtered",
        action="store_true",
        help="Flag to specify if a blank line should be showed for filtered rows"
    )

    parsed = parser.parse_args()
    namespace = {
        **parse_imports(parsed.imports, Imports.module),
        **parse_imports(parsed.vars, Imports.variable),
    }
    parsed.namespace = namespace
    # parsed.actions = parse_actions(parsed.ordered_args, namespace)
    return parsed


def main():
    args = parse_args()
    print(args)

    pipes = []
    stages = [(a, lambda _: eval(fn, {"_": _, **args.namespace}), fn) for a, fn in args.ordered_args]
    for line in sys.stdin:
        line = line.strip()
        record = Record(init=line, val=line, status=Status.VALID)
        print(f"{record = }")
        for act, fn, fn_str in stages:
            old_record = record.val
            try:
                record.val = fn(record.val)
            except Exception as e:
                record.status = Status.ERROR
                record.desc = f"Error: {e}; Init: {record.init}; Fn: {fn_str}"
                break
            if (act == "filter") and (not record.val):
                record.status = Status.FILTER
                record.desc = f"Stage: {old_record}; Init: {record.init}; Fn: {fn_str}"
                break
        print(f"{record = }")
        pipes.append(record)
        match record.status:
            case Status.ERROR | Status.FILTER:
                print(record.desc, file=sys.stderr)
            case _:
                print(record.val, file=sys.stdout)


if __name__ == "__main__":
    main()
