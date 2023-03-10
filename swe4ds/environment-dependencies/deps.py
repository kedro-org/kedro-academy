## Gaussian Processes and error bars
# Inspired by https://jakevdp.github.io/PythonDataScienceHandbook/04.03-errorbars.html

import numpy as np
import matplotlib.pyplot as plt
import sklearn
from sklearn.gaussian_process import GaussianProcess

print(np.__version__)
print(sklearn.__version__)

# define the model and draw some data
model = lambda x: x * np.sin(x)
xdata = np.array([1, 3, 5, 6, 8])
ydata = model(xdata)

# Compute the Gaussian process fit
gp = GaussianProcess(
    corr="cubic", theta0=1e-2, thetaL=1e-4, thetaU=1e-1, random_start=100
)
gp.fit(xdata[:, np.newaxis], ydata)

xfit = np.linspace(0, 10, 1000)
yfit, MSE = gp.predict(xfit[:, np.newaxis], eval_MSE=True)
dyfit = 2 * np.sqrt(MSE)  # 2*sigma ~ 95% confidence region

# Visualize the result
plt.plot(xdata, ydata, "or")
plt.plot(xfit, yfit, "-", color="gray")

plt.fill_between(xfit, yfit - dyfit, yfit + dyfit, color="gray", alpha=0.2)
plt.xlim(0, 10)
plt.savefig("errorbars.png")
