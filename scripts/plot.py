import matplotlib.pyplot as plt
import pandas as pd


def plot_ODs(filename):
    df = pd.read_csv(filename, sep="\t")

    plt.figure()
    for ii in range(1, 13):
        column = df.columns[ii]
        if "culture" in column:
            linestyle = "-"
        elif "phage_vial" in column:
            linestyle = "--"
        else:
            raise ValueError(f"Unexpected column name '{column}'")
        plt.plot(df["time"] - df["time"][0] / 3600, df[column], label=column, linestyle=linestyle)
    plt.xlabel("Time [h]")
    plt.ylabel("OD [a.u.]")
    plt.legend()
    plt.grid()


def plot_volumes(filename):
    df = pd.read_csv(filename, sep="\t")

    plt.figure()
    for ii in range(1, 13):
        column = df.columns[ii]
        if "culture" in column:
            linestyle = "-"
        elif "phage_vial" in column:
            linestyle = "--"
        else:
            raise ValueError(f"Unexpected column name '{column}'")
        plt.plot(df["time"] - df["time"][0] / 3600, df[column], label=column, linestyle=linestyle)
    plt.xlabel("Time [h]")
    plt.ylabel("Capacitance [pF]")
    plt.legend()
    plt.grid()


if __name__ == "__main__":
    plot_ODs("runs/ODs.tsv")
    plot_volumes("runs/capacitances.tsv")
    plt.show()
