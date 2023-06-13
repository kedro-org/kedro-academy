# Hints

1. You can use the `os.makedirs` function or the `pathlib.Path.mkdir` function.
2. One commonly used seed is 42, [for good reasons](https://en.wikipedia.org/w/index.php?title=Phrases_from_The_Hitchhiker%27s_Guide_to_the_Galaxy#The_Answer_to_the_Ultimate_Question_of_Life,_the_Universe,_and_Everything_is_42).
3. If you don't know how to call the outputs of `plt.subplots()`, have a look at [the matplotlib documentation](https://matplotlib.org/stable/api/index.html) for inspiration.
4. One way could be vertically stacking the series, but then we would be writing roughly the same amount of code. Try using the `pd.DataFrame` initializer with _a [dictionary comprehension](https://www.freecodecamp.org/news/dictionary-comprehension-in-python-explained-with-examples/) of NumPy arrays_.
5. The `for` loop will end up being two lines: `for x in features:` and `plot_feature()`.
6. There are 2 such variables.
7. The `for` loop will contain a `fig = plot_feature(...)` line, and then the `fig.savefig` call.
8. What about the plot label? You can intelligently use the column name, even putting the first letter into uppercase by calling an appropriate string method.
