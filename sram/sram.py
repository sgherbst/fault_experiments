# general-purpose imports
import os
import subprocess
from math import ceil, log2
from random import shuffle
from pathlib import Path

# fault-specific imports
import magma as m
import fault

# user-editable parameters
NUM_WORDS = 16
WORD_SIZE = 1
VDD = 3.3
TECH_NAME = 'scn4m_subm'
OUTPUT_PATH = 'temp'
OUTPUT_NAME = f'sram_{WORD_SIZE}_{NUM_WORDS}_{TECH_NAME}'
# do not edit anything below this line...

# file locations
THIS_DIR = Path(__file__).resolve().parent
BUILD_DIR = THIS_DIR / 'build'
OPENRAM_HOME = Path(os.environ['OPENRAM_HOME'])
OPENRAM_TECH = Path(os.environ['OPENRAM_TECH'])
MODEL_DIR = OPENRAM_TECH / TECH_NAME / 'models' / 'nom'

# define file locations
SPICE_FILES = [MODEL_DIR / 'nmos.sp',
               MODEL_DIR / 'pmos.sp',
               BUILD_DIR / OUTPUT_PATH / f'{OUTPUT_NAME}.sp']
VLOG_FILES = [BUILD_DIR / OUTPUT_PATH / f'{OUTPUT_NAME}.v']

def build_design():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # generate file for OpenRAM
    config_path = BUILD_DIR / 'myconfig.py'
    with open(config_path, 'w') as f:
        f.write(f'''\
word_size = {WORD_SIZE}
num_words = {NUM_WORDS}
tech_name = "{TECH_NAME}"
process_corners = ["TT"]
supply_voltages = [ {VDD} ]
temperatures = [ 25 ]
output_path = "{OUTPUT_PATH}"
output_name = "{OUTPUT_NAME}"
drc_name = "magic"
lvs_name = "netgen"
pex_name = "magic"\
''')

    # call OpenRAM
    cmd = []
    cmd += ['python']
    cmd += [str(OPENRAM_HOME / 'openram.py')]
    cmd += [str(config_path.stem)]
    subprocess.run(cmd, cwd=BUILD_DIR)

def run_test(target='system-verilog', simulator='iverilog'):
    # compile pin list
    ios = [
        'din0', m.In(m.Bits[WORD_SIZE]),
        'dout0', m.Out(m.Bits[WORD_SIZE]),
        'addr0', m.In(m.Bits[ceil(log2(NUM_WORDS))]),
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
    dut = m.DeclareCircuit(OUTPUT_NAME, *ios)

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
    stim = [(k, fault.random_bv(WORD_SIZE))
            for k in range(NUM_WORDS)]

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
    # kwargs['disp_type'] = 'realtime'
    if target in {'spice', 'verilog-ams'}:
        kwargs['vsup'] = VDD
        kwargs['model_paths'] = SPICE_FILES
        kwargs['bus_delim'] = '[]'
        kwargs['uic'] = True
    if target == 'system-verilog':
        kwargs['ext_libs'] = VLOG_FILES
        kwargs['ext_model_file'] = True
    if target == 'verilog-ams':
        kwargs['use_spice'] = [OUTPUT_NAME]

    # run the test
    t.compile_and_run(**kwargs)

if __name__ == '__main__':
    # build the design
    build_design()

    # run simulations
    # target, simulator = 'system-verilog', 'iverilog'
    target, simulator = 'spice', 'ngspice'
    run_test(target=target, simulator=simulator)
