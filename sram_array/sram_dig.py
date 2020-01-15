import magma as m
import fault
from random import shuffle
from pathlib import Path

# define path to circuit
THIS_DIR = Path(__file__).resolve().parent

FILES = ['sram_8_16_scn4m_subm.v']
FILES = [THIS_DIR / file for file in FILES]

def run_test(N_ADDR_BITS=4, N_DATA_BITS=8, SIMULATOR='iverilog'):
    # declare circuit
    dut = m.DeclareCircuit(
        'sram_8_16_scn4m_subm',
        'din0', m.In(m.Bits[N_DATA_BITS]),
        'dout0', m.Out(m.Bits[N_DATA_BITS]),
        'addr0', m.In(m.Bits[N_ADDR_BITS]),
        'csb0', m.BitIn,
        'web0', m.BitIn,
        'clk0', m.BitIn
    )

    # instantiate the tester
    t = fault.Tester(dut, expect_strict_default=True,
                          poke_delay_default=0)

    # write function
    def write(addr, value):
        # setup data, address, and write enable
        t.poke(dut.din0, value)
        t.poke(dut.addr0, addr)
        t.poke(dut.web0, 0)
        t.delay(1e-9)
        # produce clock rising edge and obey hold time
        t.poke(dut.clk0, 1)
        t.delay(5e-9)
        t.poke(dut.din0, 0)
        t.poke(dut.addr0, 0)
        t.poke(dut.web0, 1)
        # produce clock falling edge
        t.poke(dut.clk0, 0)
        t.delay(4e-9)

    # read function
    def check(addr, value):
        # setup data, address, and write enable
        t.poke(dut.addr0, addr)
        t.poke(dut.web0, 1)
        t.delay(1e-9)
        # produce clock rising edge and obey hold time
        t.poke(dut.clk0, 1)
        t.delay(5e-9)
        t.poke(dut.addr0, 0)
        t.poke(dut.web0, 1)
        # produce clock falling edge
        t.poke(dut.clk0, 0)
        t.delay(4e-9)
        # check output
        t.expect(dut.dout0, value)

    # initialize
    t.poke(dut.din0, 0)
    t.poke(dut.addr0, 0)
    t.poke(dut.csb0, 0)
    t.poke(dut.web0, 1)
    t.poke(dut.clk0, 0)
    t.delay(25e-9)

    # test data
    stim = [(k, fault.random_bv(N_DATA_BITS))
            for k in range(1 << N_ADDR_BITS)]

    # write data in a random order
    shuffle(stim)
    for addr, data in stim:
        write(addr, data)

    # check data in a random order
    shuffle(stim)
    for addr, data in stim:
        check(addr, data)

    # run the test
    t.compile_and_run(
        target='system-verilog',
        simulator=SIMULATOR,
        ext_libs=FILES,
        ext_model_file=True,
        disp_type='realtime'
    )

if __name__ == '__main__':
    run_test()
