import matplotlib.pyplot as plt
import pandas as pd


def plot_ODs(filename):
    df = pd.read_csv(filename, sep="\t")
    df["time"] = df["time"] - df["time"][0]

    plt.figure()
    for ii in range(1, 7):
        culture = df.columns[ii]
        phage = df.columns[ii + 6]
        (line,) = plt.plot(df["time"] / 3600, df[culture], label=culture, linestyle="-")
        plt.plot(df["time"] / 3600, df[phage], label=phage, linestyle="--", color=line.get_color())
    plt.xlabel("Time [h]")
    plt.ylabel("OD [a.u.]")
    plt.legend()
    plt.grid()


def plot_volumes(filename):
    df = pd.read_csv(filename, sep="\t")
    df["time"] = df["time"] - df["time"][0]

    plt.figure()
    for ii in range(1, 7):
        culture = df.columns[ii]
        phage = df.columns[ii + 6]
        (line,) = plt.plot(df["time"] / 3600, df[culture], label=culture, linestyle="-")
        plt.plot(df["time"] / 3600, df[phage], label=phage, linestyle="--", color=line.get_color())
    plt.xlabel("Time [h]")
    plt.ylabel("Capacitance [pF]")
    plt.legend()
    plt.grid()


if __name__ == "__main__":
    plot_ODs("runs/ODs.tsv")
    plot_volumes("runs/capacitances.tsv")
    plt.show()
