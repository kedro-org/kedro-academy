# Inspired by https://github.com/wilsonlee0601/rock
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Define the columns to compare
features = ["length_min", "danceability", "energy", "valence"]

# Calculate means for each column in each dataframe
means_rock = pd.Series(np.random.uniform(size=len(features)), index=features)
means_metal = pd.Series(np.random.uniform(size=len(features)), index=features)
means_punk = pd.Series(np.random.uniform(size=len(features)), index=features)

# Iterate over each column and create a separate bar chart
for x in features:
    f, a = plt.subplots()
    a.bar(["Rock"], means_rock[x], label="Rock")
    a.bar(["Metal"], means_metal[x], label="Metal")
    a.bar(["Punk"], means_punk[x], label="Punk")
    a.set_xlabel(" ")
    a.set_ylabel("Mean")
    a.set_title(f"Mean of {x} in the three genres")
    a.legend()
    f.savefig(f"output/{x}.png")
