import magma as m
import fault
from random import shuffle
from pathlib import Path

# convenience variable
THIS_DIR = Path(__file__).resolve().parent

# define file locations
SPICE_FILES = [THIS_DIR / 'nmos.sp',
               THIS_DIR / 'pmos.sp',
               THIS_DIR / 'sram_8_16_scn4m_subm.sp']
VLOG_FILES = [THIS_DIR / 'sram_8_16_scn4m_subm.v']

def run_test(n_addr_bits=4, n_data_bits=8, vdd=3.3, target='system-verilog',
             simulator='iverilog'):
    # compile pin list
    ios = [
        'din0', m.In(m.Bits[n_data_bits]),
        'dout0', m.Out(m.Bits[n_data_bits]),
        'addr0', m.In(m.Bits[n_addr_bits]),
        'csb0', m.BitIn,
        'web0', m.BitIn,
        'clk0', m.BitIn
    ]
    if target in {'spice', 'verilog-ams'}:
        ios += [
            'vdd', m.BitIn,
            'gnd', m.BitIn
        ]

    # declare circuit
    dut = m.DeclareCircuit('sram_8_16_scn4m_subm', *ios)

    # instantiate the tester
    t = fault.Tester(dut, poke_delay_default=0)

    # declare write function
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

    # declare read function
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

    # initialize all voltages to zero
    t.zero_inputs()
    t.delay(25e-9)

    # bring up supply while de-asserting write enable
    if target in {'spice', 'verilog-ams'}:
        t.poke(dut.vdd, 1)
    t.poke(dut.web0, 1)
    t.delay(25e-9)

    # generate test data
    stim = [(k, fault.random_bv(n_data_bits))
            for k in range(1 << n_addr_bits)]

    # write data in a random order
    shuffle(stim)
    for addr, data in stim:
        write(addr, data)

    # check data in a random order
    shuffle(stim)
    for addr, data in stim:
        check(addr, data)

    # setup arguments for test
    kwargs = {}
    kwargs['target'] = target
    kwargs['simulator'] = simulator
    kwargs['disp_type'] = 'realtime'
    if target in {'spice', 'verilog-ams'}:
        kwargs['vsup'] = vdd
        kwargs['model_paths'] = SPICE_FILES
        kwargs['bus_delim'] = '[]'
        kwargs['uic'] = True
    if target == 'system-verilog':
        kwargs['ext_libs'] = VLOG_FILES
        kwargs['ext_model_file'] = True
    if target == 'verilog-ams':
        kwargs['use_spice'] = 'sram_8_16_scn4m_subm'

    # run the test
    t.compile_and_run(**kwargs)

if __name__ == '__main__':
    run_test(target='spice', simulator='ngspice')
