import json
from typing import Any, Callable
from argparse import Namespace
from statistics import mean, median, mode, stdev, variance
from functools import reduce


class Fn:
    _FN_GROUPS = [
        ["map"],
        ["filter"],
        ["apply", "exec"],
        ["agg", "aggregate"],
        ["fold", "reduce"],
        ["filtermap", "fmap", "filter_map"],
        ["sort"],
        ["eval"]
    ]

    def __init__(self, args: Namespace):
        self.args = self._adjust_args(args)
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
            case "filtermap":
                self.filter_map()
            case "sort":
                self.sort()
            case "eval":
                self.filter_map()
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
                lambda entry: self.meta_empty(entry),
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
                sorted(self.parsed_expr, reverse=True)
            )
        else:
            output_collection = self.args.container_type(
                sorted(self.parsed_expr, key=self.args.func)
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

    def meta_empty(self, v: Any) -> bool:
        if type(v) in [set, tuple, list, dict]:
            return all([self.meta_empty(s) for s in v])
        elif v in [None, ""]:
            return False
        else:
            return True

    def _try_eval(
        self,
        fn: Callable,
        entry: str | list | tuple | dict | set,
        default: str | None = None,
    ) -> Any:
        out = default
        try:
            out = fn(entry)
        except:
            pass
        return out

    def _parse_expr(self) -> set | list | dict | tuple:
        if self.args.no_split:
            return [self.args.expr]
        if self.args.json_in:
            input_json = json.loads(self.args.expr)
            if type(input_json) == list:
                return input_json
            else:
                return [item for item in input_json.items() if item[0] is not None]
        if self.args.split_whitespace:
            the_iterable = self.args.expr.split()
        elif self.args.split_entry == "":
            the_iterable = list(self.args.expr)
        else:
            the_iterable = self.args.expr.split(self.args.input_separator)
        if self.args.split_entry in [None, ""]:
            return self.args.container_type(
                [self.args.lambda_type_lambda(entry) for entry in the_iterable]
            )
        else:
            return self.args.container_type(
                [
                    self.args.lambda_type_lambda(
                        self.args.arg_container_type(self._try_eval(self.args.type, e) for e in entry.split(self.args.split_entry))
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
        else:
            out = output
        print(out)

    def _adjust_args(self, args: Namespace) -> Namespace:
        # Reduce possible fn command names to their primary name
        for group in self._FN_GROUPS:
            if args.fn in group:
                args.fn = group[0]

        # Extract information from function and parse into a lambda
        if "->" in args.function:
            raw_vars = (
                args.function.split("->")[0]
                .replace(" ", "")
                .replace("|", "")
                .replace("(", "")
                .replace(")", "")
                .strip()
                .split(",")
            )
            raw_func = "".join(args.function.split("->")[1:]).strip()
        else:
            raw_vars = args.function.strip()[1:].split("|")[0].replace(" ", "").strip().split(",")
            raw_func = "".join(args.function.strip()[1:].split("|")[1:])
        if (
            len(args.function.split("->")) == 1
        ):  # if fn is agg, try to convert to numeric if possible
            if args.function in ["sum", "product", "stats"]:
                args.type = "int" if (args.type == "int") else "float"
        lambda_var_symbols = [s.split(":")[0].strip() for s in raw_vars]
        raw_lambda_var_types = list(
            map(
                lambda v: v[1].strip(),
                map(
                    lambda u: u[0] if (u[1] > 1) else ["", ""],
                    map(lambda t: (t.split(":"), len(t.split(":"))), raw_vars),
                ),
            )
        )
        lambda_var_types = []
        for t in raw_lambda_var_types:
            if "[" in t:
                args.type = t.split("[")[1][:-1]
                lambda_var_types.append(t.split("[")[0])
            else:
                lambda_var_types.append(t)
        lambda_var_types = [
            t
            if t in ["str", "int", "float", "bool", "list", "set", "tuple", "dict"]
            else args.type
            for t in lambda_var_types
        ]
        lambda_vars = ",".join(lambda_var_symbols)
        lambda_func = raw_func
        args.lambda_symbols = lambda_var_symbols
        lambda_inits_collection = ", ".join(
            [f"{t[1]}({t[0]})" for t in zip(lambda_var_symbols, lambda_var_types)]
        )
        lambda_inits_dict = ", ".join(
            [
                f'"{t[0]}": {t[1]}({t[0]})'
                for t in zip(lambda_var_symbols, lambda_var_types)
            ]
        )
        if type(args.arg_container_type) == "dict":
            args.lambda_type_lambda = eval(
                f"lambda {lambda_vars}: " + "{" + lambda_inits_dict + "}"
            )
        elif args.fn == "fold":
            args.lambda_type_lambda = lambda __input_var__: args.type(__input_var__)
        else:
            args.lambda_type_lambda = eval(
                f"lambda {lambda_vars}: ({lambda_inits_collection})"
            )
        if args.fn == "agg":
            args.func = lambda v: v
        elif args.fn == "eval":
            args.func = lambda s: eval(s)
        elif args.fn == "fold":
            args.func = eval(f"lambda {lambda_vars}: {lambda_func}")
        else:
            args.func = lambda entry: self._try_eval(
                eval(f"lambda {lambda_vars}: {lambda_func}"), entry
            )

        # Additional control over args to allow some to overwrite others and do necessary conversion
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
        if args.reduce_default:
            args.reduce_default = eval(args.reduce_default)
        return args

