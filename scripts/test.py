import time

from morbidostat import Morbidostat

if __name__ == "__main__":
    # tot_time = 3600 * 6
    # morb = Morbidostat()
    # morb.interface.switch_light(True)
    # time.sleep(10)
    # while morb.experiment_time() < tot_time:
    #     print(f"\n--- Experiment time: {round(morb.experiment_time(),1)}s ---")
    #     morb.record_ODs()
    #     morb.record_weights()
    #     morb.save_data()
    #     time.sleep(2 * 60)
    # print("\nExperiment is finished !")
    # morb.interface.switch_light(False)

    morb = Morbidostat()
    W = []
    for vial in morb.cultures + morb.phage_vials:
        W += [round(morb.interface.measure_WS_voltage(vial), 3)]
    print(W)
