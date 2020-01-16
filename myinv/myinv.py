import magma as m
import fault
import decida
import matplotlib.pyplot as plt
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

def sim():
    # declare circuit
    dut = m.DeclareCircuit('myinv', 'in_', m.BitIn, 'out', m.BitOut,
                           'vdd', m.BitIn, 'vss', m.BitIn)

    # define the test
    t = fault.Tester(dut, poke_delay_default=0)
    t.zero_inputs()
    t.delay(1e-9)
    t.poke(dut.vdd, True, delay=2e-9)
    t.expect(dut.out, True)
    t.poke(dut.in_, True, delay=2e-9)
    t.expect(dut.out, False)

    # run the test
    t.compile_and_run(target='spice', simulator='ngspice', vsup=1.5,
                      t_tr=1e-9, vil_rel=0.4, vih_rel=0.6,
                      model_paths=[THIS_DIR / 'myinv.sp'])

def plot():
    data = decida.Data.Data()
    data.read_nutmeg(THIS_DIR / 'build' / 'out.raw')

    t = 1e9*data.get('time')
    in_ = data.get('in_')
    out = data.get('out')
    vdd = data.get('vdd')

    ax1 = plt.subplot(311)
    plt.plot(t, vdd)
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.ylabel('vdd')
    ax1.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    ax2 = plt.subplot(312, sharex=ax1)
    plt.plot(t, in_)
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.ylabel('in_')
    ax2.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    ax3 = plt.subplot(313, sharex=ax1)
    plt.plot(t, out)
    plt.ylabel('out')
    plt.xlabel('time (ns)')
    ax3.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    plt.show()

if __name__ == '__main__':
    sim()
    plot()