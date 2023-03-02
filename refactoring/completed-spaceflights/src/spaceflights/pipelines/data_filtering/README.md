# Data filtering pipeline

## Overview

This pipeline is used to filter the rows of input table according to a column in the table. 

## Pipeline inputs

* `input_table`: `pandas.DataFrame` to be filtered
* `params:filter`: parameters dictionary containing the keys `column` (column on which to performed filter) and `value` (value to use for selecting rows) 

## Pipeline outputs

`output_table`: `pandas.DataFrame` containing only the rows of `input_table` for which `column == value`.
