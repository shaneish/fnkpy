# fnk
## python from the command line

## what it is
A command line interface with functional tendencies that allows you to parse information in the shell using Python.

## examples
when providing functions for maps and filters, the default variable used is `_`.  so long as you want to use the default variable, you can simply supply functions with that (ie, `_ + 1` , `len(_)`, etc).

#### add one to each input number and print
```console
echo -e "1\n2\n3" | fnk -m '_ + 1'
>>> 2
>>> 3
>>> 4
```
#### take list of full paths and filter out just the parent dir and current file name
```console
ls -d $PWD/*
>>> ~/scripts/fnpy/fnk/fnk.py
>>> ~/scripts/fnpy/fnk/parser.py

ls -d $PWD/* | fnk -m '"/".join(_.split(".")[-1].split("/")[-2:])'
>>> fnk/fnk
>>> fnk/parser
```
#### filter out filenames that are .py files
```console
ls
>>> fnk.py
>>> parser.py
>>> README.md
>>> random_text.txt

ls | fnk -f '".py" in _'
>>> fnk.py
>>> parser.py
```
#### removed duplicate lines from input data
```console
echo -e "same\nsame\nsame\ndifferent" | fnk -C set -m '_' -e # collect into set with `-C set`, map nothing with `-m _`, and expand output with `-e`
>>> same
>>> different
```
## future
defo needs unit tests written and defo needs multithreading support bcuz python is slow slow slow.
