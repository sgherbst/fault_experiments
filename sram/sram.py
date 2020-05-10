# general-purpose imports
import os
import subprocess
from time import time
from argparse import ArgumentParser
from pathlib import Path

def run_openram(num_words=16, word_size=2, vdd=3.3, tech_name='scn4m_subm', cwd='.'):
    # generate file for OpenRAM
    config_path = Path(cwd) / 'myconfig.py'
    with open(config_path, 'w') as f:
        f.write(f'''\
word_size = {word_size}
num_words = {num_words}
tech_name = "{tech_name}"
process_corners = ["TT"]
supply_voltages = [{vdd}]
temperatures = [ 25 ]
output_path = "temp"
output_name = "sram_{word_size}_{num_words}_{tech_name}"
drc_name = "magic"
lvs_name = "netgen"
pex_name = "magic"\
''')

    # construct OpenRAM command
    cmd = [
        'python',
        Path(os.environ['OPENRAM_HOME']) / 'openram.py',
        config_path.stem
    ]
    cmd = [str(elem) for elem in cmd]

    # call OpenRAM
    subprocess.run(cmd, cwd=cwd)

def main():
    # parse command line arguments
    parser = ArgumentParser()
    parser.add_argument('--target', type=str, default='system-verilog', help='Type of target to use.  Options are "system-verilog", "verilog-ams", and "spice".')
    parser.add_argument('--simulator', type=str, default=None, help='Simulator to use.  Options are "ncsim", "vcs", "iverilog", "vivado", "ngspice", "hspice", and "spectre".  Note that not all target/simulator pairs are valid.')
    parser.add_argument('--num_words', type=int, default=16, help='Number of words in the SRAM array.')
    parser.add_argument('--word_size', type=int, default=2, help='Number of bits in each SRAM word.')
    parser.add_argument('--vdd', type=float, default=5.0, help='VDD voltage.')
    parser.add_argument('--clk_per', type=float, default=10e-9, help='Period of the clock waveform used in testing (seconds).')
    parser.add_argument('--tech_name', type=str, default='scn4m_subm', help='Name of the process technology.')
    parser.add_argument('--manual', action='store_true')
    args = parser.parse_args()

    # create directory for building the SRAM
    this_dir = Path(__file__).resolve().parent
    ramdir = this_dir / 'build'
    ramdir.mkdir(exist_ok=True, parents=True)

    # build the OpenRAM design
    run_openram(
        num_words=args.num_words,
        word_size=args.word_size,
        vdd=args.vdd,
        tech_name=args.tech_name,
        cwd=ramdir
    )

    # set defaults
    if args.simulator is None:
        if args.target == 'system-verilog':
            args.simulator = 'iverilog'
        elif args.target == 'verilog-ams':
            args.simulator = 'ncsim'
        elif args.target == 'spice':
            args.simulator = 'ngspice'

    # determine the run directory
    if args.manual:
        if args.target in {'system-verilog', 'verilog-ams'}:
            rundir = this_dir / f'manual-sv-vams'
        elif args.target in {'spice'}:
            rundir = this_dir / f'manual-spice'
        else:
            raise Exception(f'Unknown target: {args.target}')
    else:
        rundir = 'fault'

    # determine the arguments to pass
    cmd = [
        'bash',
        'run.sh',
        args.target,
        args.simulator,
        args.num_words,
        args.word_size,
        args.vdd,
        args.clk_per,
        args.tech_name
    ]
    cmd = [str(elem) for elem in cmd]

    # run the simulation
    t0 = time()
    result = subprocess.run(cmd, cwd=rundir)
    dt = time() - t0

    if result.returncode != 0:
        raise Exception('Command failed.')

    # report result
    print(f'''\
***********************************
Target:    {args.target}
Simulator  {args.simulator}
No. words: {args.num_words}
Word size: {args.word_size}
Manual:    {args.manual}
Runtime:   {dt:0.3f} s
***********************************''')

if __name__ == '__main__':
    main()
