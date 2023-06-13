# Function complexity

The script contains a working solution to [Problem 4](https://projecteuler.net/problem=4) of Project Euler:

> A palindromic number reads the same both ways. The largest palindrome made from the product of two 2-digit numbers is 9009 = 91 × 99.
>
> Find the largest palindrome made from the product of two 3-digit numbers.

Refactor it into functions that have 1 responsibility.

## Setup

1. Create a new conda/mamba environment called `functions310` with Python 3.10.
2. Activate the environment and install `pytest` on it.
3. Execute `pytest` to verify that none of the tests pass.

## Steps

1. Create a function `is_palindrome` that receives an integer and returns `True` or `False` depending on whether the number is a palindrome or not
2. Write a function `filter_palindromes` that receives a sequence of numbers and returns a sequence containing only the numbers that are palindromes (use `is_palindrome` for it).
3. Write a function `numbers_with_n_digits` that receives an integer representing the number of digits and returns a sequence of all positive numbers with that number of digits.
4. Write a function `max_palindrome_product_with_n_digits` that receives an integer representing the number of digits and returns the maximum palindrome made from the product of two numbers with that number of digits (hence the solution of Problem 4).

Remember to document all functions with a docstring!

Extra points if you use generators (hence `yield` where appropriate).

## Extras

If you have some extra time, you can do the same with [Problem 8](https://projecteuler.net/problem=8) (optional, not graded):

> The four adjacent digits in the 1000-digit number that have the greatest product are 9 × 9 × 8 × 9 = 5832.
> [...]
> Find the thirteen adjacent digits in the 1000-digit number that have the greatest product. What is the value of this product?

## Learning Objectives

Apply some or all of these principles to function refactoring:

1. DRY (Don't Repeat Yourself)
2. SRP (Single Responsibility Principle)
3. Descriptive names
4. Group parameters
5. Isolate side effects
