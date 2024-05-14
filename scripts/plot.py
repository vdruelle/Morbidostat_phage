import matplotlib.pyplot as plt
import pandas as pd


def plot_ODs(filename):
    df = pd.read_csv(filename, sep="\t")
    df["time"] = df["time"] - df["time"][0]

    plt.figure()
    for ii in range(1, 4):
        culture = f"culture {ii}"
        phage1 = f"phage_vial {(ii-1)*3 + 1}"
        phage2 = f"phage_vial {(ii-1)*3 + 2}"
        phage3 = f"phage_vial {(ii-1)*3 + 3}"
        (line,) = plt.plot(df["time"] / 3600, df[culture], label=culture, linestyle="-")
        plt.plot(df["time"] / 3600, df[phage1], label=phage1, linestyle="--", color=line.get_color())
        plt.plot(df["time"] / 3600, df[phage2], label=phage2, linestyle=":", color=line.get_color())
        plt.plot(df["time"] / 3600, df[phage3], label=phage3, linestyle="dashdot", color=line.get_color())
    plt.xlabel("Time [h]")
    plt.ylabel("OD [a.u.]")
    plt.legend()
    plt.grid()


def plot_volumes(filename):
    df = pd.read_csv(filename, sep="\t")
    df["time"] = df["time"] - df["time"][0]

    plt.figure()
    for ii in range(1, 4):
        culture = f"culture {ii}"
        phage1 = f"phage_vial {(ii-1)*3 + 1}"
        phage2 = f"phage_vial {(ii-1)*3 + 2}"
        phage3 = f"phage_vial {(ii-1)*3 + 3}"
        (line,) = plt.plot(df["time"] / 3600, df[culture], label=culture, linestyle="-")
        plt.plot(df["time"] / 3600, df[phage1], label=phage1, linestyle="--", color=line.get_color())
        plt.plot(df["time"] / 3600, df[phage2], label=phage2, linestyle=":", color=line.get_color())
        plt.plot(df["time"] / 3600, df[phage3], label=phage3, linestyle="dashdot", color=line.get_color())
    plt.xlabel("Time [h]")
    plt.ylabel("Capacitance [pF]")
    plt.legend()
    plt.grid()


if __name__ == "__main__":
    plot_ODs("runs/ODs.tsv")
    plot_volumes("runs/capacitances.tsv")
    plt.show()
