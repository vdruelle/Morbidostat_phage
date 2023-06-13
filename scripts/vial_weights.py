import matplotlib.pyplot as plt
import numpy as np

vial_weights = [
    24.12,
    23.91,
    23.86,
    23.7,
    24.14,
    23.99,
    23.67,
    23.67,
    23.84,
    24.05,
    23.60,
    24.14,
    24.08,
    24.09,
    24.18,
    23.86,
    23.94,
    23.82,
    23.67,
    24.04,
    24.11,
    23.83,
    23.70,
    23.78,
]

caps = [53, 51, 52, 54, 54, 50, 54, 54, 54, 52, 55, 55, 54, 53, 54, 53, 54]
caps = np.array(caps) * 0.01 + 9

plt.figure()
plt.hist(vial_weights, bins=np.arange(23.6, 24.3, 0.1))
plt.xlabel("Weight [g]")
plt.ylabel("Occurences")


plt.figure()
plt.hist(caps, bins=np.arange(9.5, 9.6, 0.01))
plt.xlabel("Weight [g]")
plt.ylabel("Occurences")
plt.show()
