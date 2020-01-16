import numpy as np
import magma as m
import fault
import matplotlib.pyplot as plt
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

def sim():
    # declare circuit
    dut = m.DeclareCircuit('myinv', 'in_', fault.RealIn, 'out', fault.RealOut,
                           'vdd', fault.RealIn, 'vss', fault.RealIn)
    t = fault.Tester(dut, poke_delay_default=0)
    t.zero_inputs()
    t.poke(dut.vdd, 1.5, delay=2e-9)
    out = []
    for in_ in np.linspace(0, 1.5, 100):
        t.poke(dut.in_, in_, delay=2e-9)
        out.append(t.get_value(dut.out))

    # run the test
    t.compile_and_run(target='spice', simulator='ngspice', vsup=1.5,
                      t_tr=1e-9, model_paths=[THIS_DIR / 'myinv.sp'])

    # extract outputs
    out = [elem.value for elem in out]

    return out
def plot(out):
    plt.plot(np.linspace(0, 1.5, 100), out)
    plt.xlabel('in_')
    plt.ylabel('out')
    plt.savefig(THIS_DIR / 'myinv_tf.pdf', bbox_inches='tight', pad_inches=0)

if __name__ == '__main__':
    out = sim()
    plot(out)