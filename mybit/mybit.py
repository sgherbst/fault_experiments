import magma as m
import fault
import decida
import matplotlib.pyplot as plt
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

def sim():
    # declare circuit
    dut = m.DeclareCircuit('mybit', 'lbl', m.BitInOut, 'lblb', m.BitInOut,
                           'wl', m.BitIn, 'vdd', m.BitIn, 'vss', m.BitIn)

    # define the test
    t = fault.Tester(dut, poke_delay_default=0)
    t.zero_inputs()
    t.delay(10e-9)
    t.poke(dut.vdd, True)
    # write
    t.poke(dut.lbl, True)
    t.poke(dut.lblb, False, delay=10e-9)
    t.poke(dut.wl, True, delay=10e-9)
    t.poke(dut.wl, False, delay=10e-9)
    # precharge
    t.poke(dut.lbl, True)
    t.poke(dut.lblb, True, delay=10e-9)
    # read
    t.poke(dut.lbl, fault.HiZ)
    t.poke(dut.lblb, fault.HiZ, delay=10e-9)
    t.poke(dut.wl, 1, delay=10e-9)
    t.expect(dut.lbl, True)
    t.expect(dut.lblb, False)
    t.poke(dut.wl, 0, delay=10e-9)

    # run the test
    t.compile_and_run(target='spice', simulator='ngspice', vsup=1.5,
                      t_tr=1e-9, model_paths=[THIS_DIR / 'mybit.sp'])

def plot():
    data = decida.Data.Data()
    data.read_nutmeg(THIS_DIR / 'build' / 'out.raw')

    t = 1e9*data.get('time')
    wl = data.get('wl')
    lbl = data.get('lbl')
    lblb = data.get('lblb')

    ax1 = plt.subplot(311)
    plt.plot(t, wl)
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.ylabel('wl')
    ax1.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    ax2 = plt.subplot(312, sharex=ax1)
    plt.plot(t, lbl)
    plt.setp(ax2.get_xticklabels(), visible=False)
    plt.ylabel('lbl')
    ax2.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    ax3 = plt.subplot(313, sharex=ax1)
    plt.plot(t, lblb)
    plt.ylabel('lblb')
    plt.xlabel('time (ns)')
    ax3.xaxis.grid()
    plt.yticks([0, 1.5], ['0', '1.5'])

    plt.show()

if __name__ == '__main__':
    sim()
    plot()
