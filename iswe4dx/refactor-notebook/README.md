# Refactor a notebook

You are given a script that produces a series of plots in the `outputs` directory. Refactor it to make it more modular and maintainable.

## Setup

1. Create a new conda/mamba environment called `refactor310` with Python 3.10.
2. Activate it and proceed with the following steps.

## Steps

Follow these steps one by one. If you get stuck, have a look at `hints.md` (but only as a last resort!)

1. Copy and paste the contents of the notebook to a script called `refactor.py`.
2. Run the script once. It will fail because there's no `output` directory - looks like our colleague assumed we would create it. Rather than doing it by hand, add a conditional that creates the directory if it does not exist.
2. The script contains calls to functions from `np.random`, and therefore everytime it's run will produce a different result. Verify this fact (run the script, see one image, close image, run script again, open image, verify they're different). To prevent this, add a `np.random.seed` at the top of the script, hardcoding a seed of your choosing. Verify the fix.
3. There are a few variables with one-letter names. This harms readability and as such is considered a bad practice. Rename them to have more explicit names (don't need to be full words, but definitely not one character). _Note that, if you right-click a variable, an action to rename all occurrences will be shown!_
4. Three `pd.Series` are created with exactly the same logic. Rather than having 3 different variables, replace them by a single `pd.DataFrame` called `df`, where the index is the column names and the columns are the genres (there are various ways to do this). Update the plotting code accordingly.
5. Put all the plotting code (lines inside the `for` loop) inside a `plot_feature` function. For now, don't give it any parameters.
6. The function uses some variables that are declared outside of it. Can you identify them? Turn them into parameters so that the function is self-contained.
7. Still, the function has one side effect: saving a figure to the `output` directory. In the spirit of minimizing the amount of side effects inside our functions, remove that line, replace it by an appropriate `return` statement, and bring the `.savefig` call back to the `for` loop, where it was before.
8. What happens if someone adds more genres in the future? Correct: our function would only plot the 3 hardcoded genres we initially considered. Turn the repeated `ax.bar` calls into a `for` loop iterating over the `DataFrame` columns.

Verify that it's trivial now to change the feature names or the genre names, since you only have to change them in one place, and the function doesn't change at all.

Well done!
