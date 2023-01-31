# fnk
## python from the command line

## what it is
A command line interface with functional tendencies that allows you to parse information in the shell using Python.

## examples

**note on defining closures/lambdas**
Functions (`-f` and `--function`) can be defined using a variety of function formats, one of them being the default Rust format for closures and another explicitly showing the mapping.  The below are all valid ways to write your functions (each example does the same thing, add one to a list of input numbers):
  1) `|x: int| x + 1`
  2) `x: int -> x + 1`
  3) `(x: int) -> x + 1`
  4) `|x: int| -> x + 1`
I prefer the top format shown in 1), but you do you boo boo.  Examples below are written in the mixed form show in 4) above just to make it absolutely clear what the variable and function declarations are.

Note on the note: if you want to treat the input data as strings, you don't need to specify type.  For example:
  `|s| -> s + "concat to end of s"`
Additionally, if you're using a uniform type for all variables, you can also just specify the type using the `-t`/`--type` flag:
  `fnk map -f '|n| -> n + 1' -t int`
The above function is functionally equivalent to the examples shown in 1 - 4).

#### add one to each input number and print
```bash
echo -e "1\n2\n3" | fnk map -f '|n: int| -> n + 1'
>>> 2
>>> 3
>>> 4
```
#### add one to each input number and sum
```bash
echo -e "1\n2\n3" | fnk map -f '|n: int| -> n + 1' | fnk agg -f sum
>>> 11
```
#### take list of full paths and filter out just the parent dir and current file name
```bash
ls -d $PWD/*
>>> ~/scripts/fnpy/fnk/fnk.py
>>> ~/scripts/fnpy/fnk/parser.py

ls -d $PWD/* | fnk map -f '|f: str| -> "/".join(f.split(".")[-1].split("/")[-2:])'
>>> fnk/fnk
>>> fnk/parser
```
#### take input and split each word into it's own line
```bash
echo -e "words on a line\nand between lines" | fnk map --split_whitespace
>>> words
>>> on
>>> a
>>> line
>>> and
>>> between
>>> lines
```
#### filter out filenames that are .py files
```bash
ls
>>> fnk.py
>>> parser.py
>>> README.md
>>> random_text.txt

ls | fnk filter -f '|s: str| ".py" in s'
>>> fnk.py
>>> parser.py
```
#### removed duplicate lines from input data
```bash
echo -e "same\nsame\nsame\ndifferent" | fnk map -container_type set
>>> same
>>> different
```
#### read input as json, filter name `name` key, filter out entries without a `name` key, and prepend with "Name: "
```bash
echo '[{"name": "shane", "age": 35}, {"name": "dan", "age": 31}, {"age": 22}]' | fnk filtermap -f '|entry| -> "Name: " + entry.get("name", "")' --json_in
>>> shane
>>> dan
```
#### read current list of files, import `os` module, and use to delete everything with "tempnvim" in it

```bash
ls
>>> c:usersstephlocaltempvnim.alk1231l
>>> c:userstephlocaltempnvim.asdl213k1
>>> fnk.py
>>> parser.py

ls | fnk filter -f '|f| -> "tempnvim" in f' | fnk apply -f '|f| os.remove(f)' --modules os
>>> fnk.py
>>> parser.py
```

#### evaluate a simple expression from the command line
If you want to manually input your input data instead of piping it in, you can do that as follows:
```bash
# note that both functions below are functionally equivalent, eval just evaluates each line of input.
fnk eval "1 + 1"
>>> 2

fnk filtermap "1 + 1" -f "|e| eval(e)"
>>> 2
```

#### calculate stats on a string of numbers from the command line
```bash
fnk agg "1,2,3" -f stats --input_separator ,
>>> Mean   -> 2.0
>>> Median -> 2.0
>>> Mode   -> 1.0
>>> Stdev  -> 1.0
>>> Var    -> 1.0

echo "1 2 3" | fnk agg -f stats --split_whitespace
>>> Mean   -> 2.0
>>> Median -> 2.0
>>> Mode   -> 1.0
>>> Stdev  -> 1.0
>>> Var    -> 1.0

echo -e "1\n2\n3" | fnk agg -f stats
>>> Mean   -> 2.0
>>> Median -> 2.0
>>> Mode   -> 1.0
>>> Stdev  -> 1.0
>>> Var    -> 1.0
```


## future
defo needs unit tests written and defo needs multithreading support bcuz python is slow slow slow.
