# fnkpy rewrite notes

### general overview
- get rid of ugly first required arg ('fnk filter', 'fnk map', etc)
- allow specifying multiple combinations of maps and filters with a single command (ie, `fnk --filter 'int(_.split(".")[1])' --map '_ * 2' --filter '_ >= 2'` will apply the first filter, the map after it, then the final filter in that order)
- look at including additional flags
  * `--reduce` (`-r`) flag which will allow you to use `functools.reduce()` on the final output
  * `--apply` (`-a`) flag which will allow you to apply a shell command to each line of output
    - should use `os.system()` on each output line and then pipe each successful system call (ie, returns 0) to stdout and failed system calls to stderr
- config file/folder:
  * store larger functions and modules for common use
  * set default imports
  * set default variable identifier
- support complex imports
  * `--import json>loads=jl` -> `from json import loads as jl`
  * `--import os` -> `import os`
  * `--import os=uwu` -> `import os as uwu`
  * `--import json>loads,dumps` -> `from json import loads, dumps`
  * `--import json>loads=jl json>dumps=dl` -> `from json import loads as jl; from json import dumps as ds`
- multi-threaded support for faster operations
  * possibly use [queues](https://docs.python.org/3/library/queue.html) or [threading](https://code.activestate.com/recipes/577360-a-multithreaded-concurrent-version-of-map/)
  * can also try [a mix of queues and threads](https://stackoverflow.com/questions/3329361/python-something-like-map-that-works-on-threads)
- pipe stdout and stderr to actual stdout and stderr
- system for allowing users to specify function application via `eval()` or `exec()`
- include separate namespace that will be used for evaluation and execution of functions
  * specific flag `--variable` (`-V`) to allow users to set unique namespace variables to use: `--variable pi=3.14 empty=[]`
  * possibly include flags for universal namespace variables and operation-scoped namespace variables which are only added to namespace for the next immediate function
  * examples:
    + `lambda _: eval(_ + offset, {'_': _, 'offset': 2})`
    + `d = 0; lambda _: exec(d = d + int(_.split(':')), {'_': _, 'd': d})`
- possibly specify whether chained functions should be applied horizontally or vertically
  * horizontally means `--map '_.split(".")[0]' --filter 'int(_) > 0'` will be applied as `filter(lambda _: int(_.split(".")[0]), __)`
  * vertically means `--map '_.split(".")[0]' --filter 'int(_) > 0'` will be applied as `filter(lambda _: int(_) > 0, map(lambda _: _.split(".")[0], __))`

### refs
---

**parse multiple flag args in order with duplicates**
stolen from [stackoverflow](https://stackoverflow.com/questions/9027028/argparse-argument-order)
```python
import argparse

class OrderedArgsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not 'ordered_args' in namespace:
            setattr(namespace, 'ordered_args', [])
        previous = namespace.ordered_args
        previous.append((self.dest, values))
        setattr(namespace, 'ordered_args', previous)

parser = argparse.ArgumentParser()
parser.add_argument('--filter', '-f', action=OrderedArgsAction)
parser.add_argument('--map', '-m', action=OrderedArgsAction)
parser.add_argument('--input-row-sep', '-IRS', default='\n', type=str)

parser.parse_args(['-m', 'int(_.split(".")[1])', '-f', '_ > 2', '--map', '_ * 2', '-IRS', '\n\n'])
```
Should produce following output, where `ordered_orgs` gives a list of tuples that commands can be run in order:
> >>> Namespace(filter=None, map=None, ordered_args=[('map', 'int(_.split(".")[1])'), ('filter', '_ > 2'), ('map', '_ * 2')], input_row_sep='\n\n')

---

**pipe text to stdout and stderr**
```python
import sys

print("to stdout", file=sys.stdout)
print("to stderr", file=sys.stderr)
```

---
