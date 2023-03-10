# import pytest

from function_complexity import (
    max_palindrome_product_with_n_digits,
    numbers_with_n_digits,
    filter_palindromes,
    is_palindrome,
)


def test_max_palindrome_product_with_n_digits_returns_correct_solution():
    assert max_palindrome_product_with_n_digits(2) == 9009
    assert max_palindrome_product_with_n_digits(3) == 906609


def test_numbers_with_n_digits_returns_correct_result():
    assert len(list(numbers_with_n_digits(1))) == 9
    assert len(list(numbers_with_n_digits(2))) == 100 - 10
    assert len(list(numbers_with_n_digits(3))) == 1_000 - 100


def test_filter_palindromes_returns_correct_result():
    assert list(filter_palindromes([11, 242, 13])) == [11, 242]
    assert list(filter_palindromes([31, 76, 777])) == [777]
    assert list(filter_palindromes([222, 91, 8009008])) == [222, 8009008]


def test_is_palindrome_returns_correct_result():
    assert not is_palindrome(123)
    assert not is_palindrome(112)
    assert is_palindrome(131)
    assert is_palindrome(242)
    assert is_palindrome(9000009)
