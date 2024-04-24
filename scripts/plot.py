import matplotlib.pyplot as plt
import pandas as pd


def plot_ODs(filename):
    df = pd.read_csv(filename, sep="\t")

    plt.figure()
    for ii in range(1, 13):
        column = df.columns[ii]
        plt.plot(df["time"], df[column], label=column)
    plt.xlabel("Time [s]")
    plt.ylabel("OD [a.u.]")
    plt.legend()
    plt.grid()


def plot_volumes(filename):
    df = pd.read_csv(filename, sep="\t")

    plt.figure()
    for ii in range(1, 13):
        column = df.columns[ii]
        plt.plot(df["time"], df[column], label=column)
    plt.xlabel("Time [s]")
    plt.ylabel("Capacitance [pF]")
    plt.legend()
    plt.grid()


if __name__ == "__main__":
    plot_ODs("runs/ODs.tsv")
    plot_volumes("runs/capacitances.tsv")
    plt.show()
