# general includes
import os
import sys
from math import ceil, log2
from random import shuffle
from pathlib import Path

# fault-specific includes
import magma as m
import fault

# read out arguments
target = sys.argv[1]
simulator = sys.argv[2]
num_words = int(sys.argv[3])
word_size = int(sys.argv[4])
vdd = float(sys.argv[5])
clk_per = float(sys.argv[6])
tech_name = sys.argv[7]

# determine where files are located
this_dir = Path(__file__).resolve().parent
ram_dir = this_dir.parent / 'build' / 'temp'
model_dir = Path(os.environ['OPENRAM_TECH']) / tech_name / 'models' / 'nom'

# determine the name of the SRAM
output_name = f'sram_{word_size}_{num_words}_{tech_name}'

# compile pin list
io_dict = dict(
    din0=m.In(m.Bits[word_size]),
    dout0=m.Out(m.Bits[word_size]),
    addr0=m.In(m.Bits[ceil(log2(num_words))]),
    csb0=m.BitIn,
    web0=m.BitIn,
    clk0=m.BitIn
)
if target in {'spice', 'verilog-ams'}:
    io_dict.update(dict(
        vdd=m.BitIn,
        gnd=m.BitIn
    ))

# declare circuit
class dut(m.Circuit):
    name = output_name
    io = m.IO(**io_dict)

# instantiate the tester
t = fault.Tester(dut, poke_delay_default=0)

# declare write function
def write(addr, value):
    # setup data, address, and write enable
    t.poke(dut.din0, value)
    t.poke(dut.addr0, addr)
    t.poke(dut.web0, 0)
    t.delay(0.1 * clk_per)
    # produce clock rising edge and obey hold time
    t.poke(dut.clk0, 1)
    t.delay(0.5 * clk_per)
    t.poke(dut.din0, 0)
    t.poke(dut.addr0, 0)
    t.poke(dut.web0, 1)
    # produce clock falling edge
    t.poke(dut.clk0, 0)
    t.delay(0.4 * clk_per)

# declare read function
def check(addr, value):
    # setup data, address, and write enable
    t.poke(dut.addr0, addr)
    t.poke(dut.web0, 1)
    t.delay(0.1 * clk_per)
    # produce clock rising edge and obey hold time
    t.poke(dut.clk0, 1)
    t.delay(0.5 * clk_per)
    t.poke(dut.addr0, 0)
    t.poke(dut.web0, 1)
    # produce clock falling edge
    t.poke(dut.clk0, 0)
    t.delay(0.4 * clk_per)
    # check output
    t.expect(dut.dout0, value)

# initialize all voltages to zero
t.zero_inputs()
t.delay(5 * clk_per)

# bring up supply while de-asserting write enable
if target in {'spice', 'verilog-ams'}:
    t.poke(dut.vdd, 1)
t.poke(dut.web0, 1)
t.delay(5 * clk_per)

# generate test data
stim = [(k, fault.random_bv(word_size))
        for k in range(num_words)]

# write data in a random order
shuffle(stim)
for addr, data in stim:
    write(addr, data)

# check data in a random order
shuffle(stim)
for addr, data in stim:
    check(addr, data)

# make the build directory
build_dir = this_dir / 'build'
build_dir.mkdir(exist_ok=True, parents=True)

# setup arguments for test
kwargs = {}
kwargs['target'] = target
kwargs['simulator'] = simulator
kwargs['directory'] = build_dir
kwargs['disp_type'] = 'realtime'
if target in {'spice', 'verilog-ams'}:
    kwargs['vsup'] = vdd
    kwargs['model_paths'] = [
        model_dir / 'nmos.sp',
        model_dir / 'pmos.sp',
        ram_dir / f'{output_name}.sp'
    ]
    kwargs['bus_delim'] = '[]'
if target == 'spice':
    kwargs['uic'] = True
if target == 'system-verilog':
    kwargs['ext_libs'] = [ram_dir / f'{output_name}.v']
    kwargs['ext_model_file'] = True
if target == 'verilog-ams':
    kwargs['use_spice'] = [output_name]

# run the test
t.compile_and_run(**kwargs)