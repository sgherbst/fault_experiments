# general-purpose imports
import os
import subprocess
from time import time
from argparse import ArgumentParser
from math import ceil, log2
from random import shuffle
from pathlib import Path

# fault-specific imports
import magma as m
import fault

class RamCfg:
    def __init__(self, num_words=16, word_size=1, vdd=3.3,
                 tech_name='scn4m_subm', clk_per=10e-9):
        self.num_words = num_words
        self.word_size = word_size
        self.vdd = vdd
        self.tech_name = tech_name
        self.clk_per = clk_per
        self.output_path = 'temp'
        self.output_name = f'sram_{self.word_size}_{self.num_words}_{self.tech_name}'
        self.build_dir = Path(__file__).resolve().parent / 'build'
        self.openram_home = Path(os.environ['OPENRAM_HOME'])
        self.openram_tech = Path(os.environ['OPENRAM_TECH'])
        self.model_dir = self.openram_tech / self.tech_name / 'models' / 'nom'
        self.spice_files = [self.model_dir / 'nmos.sp',
                            self.model_dir / 'pmos.sp',
                            self.build_dir / self.output_path / f'{self.output_name}.sp']
        self.vlog_files = [self.build_dir / self.output_path / f'{self.output_name}.v']

def build_design(ram_cfg):
    ram_cfg.build_dir.mkdir(parents=True, exist_ok=True)

    # generate file for OpenRAM
    config_path = ram_cfg.build_dir / 'myconfig.py'
    with open(config_path, 'w') as f:
        f.write(f'''\
word_size = {ram_cfg.word_size}
num_words = {ram_cfg.num_words}
tech_name = "{ram_cfg.tech_name}"
process_corners = ["TT"]
supply_voltages = [ {ram_cfg.vdd} ]
temperatures = [ 25 ]
output_path = "{ram_cfg.output_path}"
output_name = "{ram_cfg.output_name}"
drc_name = "magic"
lvs_name = "netgen"
pex_name = "magic"\
''')

    # call OpenRAM
    cmd = []
    cmd += ['python']
    cmd += [str(ram_cfg.openram_home / 'openram.py')]
    cmd += [str(config_path.stem)]
    subprocess.run(cmd, cwd=ram_cfg.build_dir)

def run_test(ram_cfg, target='system-verilog', simulator='iverilog'):
    # compile pin list
    ios = [
        'din0', m.In(m.Bits[ram_cfg.word_size]),
        'dout0', m.Out(m.Bits[ram_cfg.word_size]),
        'addr0', m.In(m.Bits[ceil(log2(ram_cfg.num_words))]),
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
    dut = m.DeclareCircuit(ram_cfg.output_name, *ios)

    # instantiate the tester
    t = fault.Tester(dut, poke_delay_default=0)

    # declare write function
    def write(addr, value):
        # setup data, address, and write enable
        t.poke(dut.din0, value)
        t.poke(dut.addr0, addr)
        t.poke(dut.web0, 0)
        t.delay(0.1 * ram_cfg.clk_per)
        # produce clock rising edge and obey hold time
        t.poke(dut.clk0, 1)
        t.delay(0.5 * ram_cfg.clk_per)
        t.poke(dut.din0, 0)
        t.poke(dut.addr0, 0)
        t.poke(dut.web0, 1)
        # produce clock falling edge
        t.poke(dut.clk0, 0)
        t.delay(0.4 * ram_cfg.clk_per)

    # declare read function
    def check(addr, value):
        # setup data, address, and write enable
        t.poke(dut.addr0, addr)
        t.poke(dut.web0, 1)
        t.delay(0.1 * ram_cfg.clk_per)
        # produce clock rising edge and obey hold time
        t.poke(dut.clk0, 1)
        t.delay(0.5 * ram_cfg.clk_per)
        t.poke(dut.addr0, 0)
        t.poke(dut.web0, 1)
        # produce clock falling edge
        t.poke(dut.clk0, 0)
        t.delay(0.4 * ram_cfg.clk_per)
        # check output
        t.expect(dut.dout0, value)

    # initialize all voltages to zero
    t.zero_inputs()
    t.delay(5 * ram_cfg.clk_per)

    # bring up supply while de-asserting write enable
    if target in {'spice', 'verilog-ams'}:
        t.poke(dut.vdd, 1)
    t.poke(dut.web0, 1)
    t.delay(5 * ram_cfg.clk_per)

    # generate test data
    stim = [(k, fault.random_bv(ram_cfg.word_size))
            for k in range(ram_cfg.num_words)]

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
    kwargs['directory'] = ram_cfg.build_dir
    kwargs['disp_type'] = 'realtime'
    if target in {'spice', 'verilog-ams'}:
        kwargs['vsup'] = ram_cfg.vdd
        kwargs['model_paths'] = ram_cfg.spice_files
        kwargs['bus_delim'] = '[]'
    if target == 'spice':
        kwargs['uic'] = True
    if target == 'system-verilog':
        kwargs['ext_libs'] = ram_cfg.vlog_files
        kwargs['ext_model_file'] = True
    if target == 'verilog-ams':
        kwargs['use_spice'] = [ram_cfg.output_name]

    # run the test
    t.compile_and_run(**kwargs)

def main():
    # parse command line arguments
    parser = ArgumentParser()
    parser.add_argument('--target', type=str, default='system-verilog', help='Type of target to use.  Options are "system-verilog", "verilog-ams", and "spice".')
    parser.add_argument('--simulator', type=str, default=None, help='Simulator to use.  Options are "ncsim", "vcs", "iverilog", "vivado", "ngspice", "hspice", and "spectre".  Note that not all target/simulator pairs are valid.')
    parser.add_argument('--num_words', type=int, default=16, help='Number of words in the SRAM array.')
    parser.add_argument('--word_size', type=int, default=1, help='Number of bits in each SRAM word.')
    parser.add_argument('--vdd', type=float, default=3.3, help='VDD voltage.')
    parser.add_argument('--tech_name', type=str, default='scn4m_subm', help='Name of the process technology.')
    parser.add_argument('--clk_per', type=float, default=10e-9, help='Period of the clock waveform used in testing (seconds).')
    args = parser.parse_args()

    # set defaults
    if args.simulator is None:
        if args.target == 'system-verilog':
            args.simulator = 'iverilog'
        elif args.target == 'verilog-ams':
            args.simulator = 'ncsim'
        elif args.target == 'spice':
            args.simulator = 'ngspice'

    # create the RAM configuration
    ram_cfg = RamCfg(num_words=args.num_words, word_size=args.word_size,
                     vdd=args.vdd, tech_name=args.tech_name,
                     clk_per=args.clk_per)

    # build the OpenRAM design
    build_design(ram_cfg)

    # run the simulation
    t0 = time()
    run_test(ram_cfg, target=args.target, simulator=args.simulator)
    dt = time() - t0

    # report result
    print(f'''\
***********************************
Target:    {args.target}
Simulator  {args.simulator}
No. words: {ram_cfg.num_words}
Word size: {ram_cfg.word_size}
Runtime:   {dt:0.3f} s
***********************************''')

if __name__ == '__main__':
    main()
