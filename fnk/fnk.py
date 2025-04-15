import sys
from importlib import metadata
from typing import Any, Sequence, Iterable
from argparse import ArgumentParser, Namespace, Action
from importlib import import_module
from enum import Enum
from dataclasses import dataclass
if sys.version_info > (3, 10):
    from typing import Self
else:
    from typing_extensions import Self


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
    def infer(cls, repr: str) -> Self | None:
        if repr:
            match repr.lower():
                case '[]' | 'list':
                    return Collection.LIST
                case '{}' | 'set':
                    return Collection.SET
                case '()' | 'tuple':
                    return Collection.TUPLE
                case _:
                    return None


@dataclass
class Record:
    val: Any
    status: Status

    def update(self, **kwargs) -> Self:
        for k in self.__dataclass_fields__.keys():
            self.__dict__[k] = kwargs.get(k) or self.__dict__[k]
        return self


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
        "-C",
        "--collect",
        type=str,
        help="Collection type to collect all lines into prior to applying maps or evals"
    )
    parser.add_argument(
        "--constants",
        "-c",
        type=str,
        nargs="*",
        help="Additional constants to add to execution namespace.  Should be supplied in format `--variables var_name=var_val 'extra_string=Hello there' two=2`",
    )
    parser.add_argument(
        "--variable-repr",
        "-V",
        type=str,
        default="_",
        help="Variable name to use across stages, default is '_'",
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
        "-bf",
        "--blank-line-filtered",
        action="store_true",
        help="Flag to specify if a blank line should be showed for filtered rows"
    )
    parser.add_argument(
        "-be",
        "--blank-line-exceptions",
        action="store_true",
        help="Flag to specify if a blank line should be showed for exception rows"
    )
    parser.add_argument(
        "-se",
        "--show-exceptions",
        action="store_true",
        help="Flag to print exception messages into stderr"
    )
    parser.add_argument(
        "-sf",
        "--show-filtered",
        action="store_true",
        help="Flag to print error into stderr"
    )
    parser.add_argument(
        "-e",
        "--expand",
        action="store_true",
        help="Flag to expand collected elements back into individual records prior to sending back to stdout/stderr"
    )

    parsed = parser.parse_args()
    namespace = {
        **parse_imports(parsed.imports, Imports.module),
        **parse_imports(parsed.constants, Imports.variable),
    }
    parsed.collection = Collection.infer(parsed.collect)
    parsed.namespace = namespace
    return parsed


# i know the below function can be made prettier by abstracting out a bunch of
# the logic (ie, the actual evaluation part, splitting into two other functions
# where one handles collections and the other handles evaluations, etc),
# but due to the heavy performance hit incurred by function
# calls python and my reluctance to duplicate the same code in two separate
# functions in case it needs to be changed i've just thrown it together as you
# see below.
#
# sue me
def evaluate(collection: Iterable, args: Namespace, return_evaluation: bool = False) -> list[Record] | None:
    if args.debug:
        print("NAMESPACE:", args, "\n")
    records = []
    if args.collection:
        collected = args.collection.value(element.strip() for element in collection)
        collection = [collected]
    for element in collection:
        element = element if not isinstance(element, str) else element.strip()
        record = Record(val=element, status=Status.VALID)
        # the below for-loop evaluates the output value of each input element across all maps/filters at one time
        for act, fn_str in args.ordered_args:
            try:
                # fn = lambda _: eval(fn_str, {"_": _, **args.namespace})
                # output = fn(record.val)
                output = eval(fn_str, {args.variable_repr: record.val, **args.namespace})
                if args.debug:
                    print(f"VALID: {record = }, {output = }, {fn_str = }")
            except Exception as e: # skip excepted elements
                record = record.update(val=e, status=Status.ERROR)
                if args.debug:
                    print(f"EXCEPTION: {record = }, {act = }, {fn_str = }\n")
                break
            if act == "filter": # skip filtered elements or pass through previous evaluated value
                if not output:
                    record = record.update(val=output, status=Status.FILTER)
                    if args.debug:
                        print(f"FILTERED: {record = }, {act = }, {fn_str = }\n")
                    break
            else: # pass through valid elements that weren't filtered
                record = record.update(val=output)
        new_records = [record]
        if args.collection and args.expand: # expand records back out if collected and expand is selected
            new_records = [Record(val=v, status=Status.VALID) for v in record.val]
        if not return_evaluation:
            for new_record in new_records:
                match new_record.status:
                    case Status.ERROR:
                        if args.show_exceptions:
                            print(new_record.val, file=sys.stderr)
                        if args.blank_line_exceptions:
                            print("", file=sys.stdout)
                    case Status.FILTER:
                        if args.show_filtered:
                            print(new_record.val, file=sys.stderr)
                        if args.blank_line_filtered:
                            print("", file=sys.stdout)
                    case _:
                        if args.debug:
                            print(f"OUTPUT: {new_record.val}\n", file=sys.stdout)
                        else:
                            print(new_record.val, file=sys.stdout)
        else:
            records = records + new_records
    return records


def main():
    args = parse_args()
    if args.version:
        print(f"fnk {metadata.version('fnk')}")
    else:
        evaluate(sys.stdin, args)


if __name__ == "__main__":
    main()
