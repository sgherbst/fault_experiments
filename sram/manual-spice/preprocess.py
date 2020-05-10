import os
import sys
import pickle
from random import randint, shuffle
from math import log2, ceil
from pathlib import Path

class Time:
    def __init__(self):
        self.t = 0

    def incr(self, dt):
        self.t += dt

class VoltageSource:
    def __init__(self, name, drive=None, t_tr=1e-12):
        self.name = name
        self.drive = drive if drive is not None else name
        self.t_tr = t_tr
        self.pts = [(0, 0.0)]

    def put(self, v, t):
        self.pts.append((t-self.t_tr, self.pts[-1][1]))
        self.pts.append((t, v))

    def compile(self, t):
        # add final point
        pts = self.pts
        pts += [(t, self.pts[-1][1])]

        # set DC level
        dc = f'DC {pts[0][1]}'

        # PWL waveform
        pwl = ' '.join([f'{pt[0]} {pt[1]}' for pt in pts])
        pwl = f'PWL({pwl})'

        # full SPICE instantiation
        return f'V{self.name} {self.drive} 0 {dc} {pwl}'

# read out arguments
target = sys.argv[1]
simulator = sys.argv[2]
num_words = int(sys.argv[3])
word_size = int(sys.argv[4])
vdd = float(sys.argv[5])
clk_per = float(sys.argv[6])
tech_name = sys.argv[7]

# derive number of address bits
addr_size = int(ceil(log2(num_words)))

# determine where files are located
this_dir = Path(__file__).resolve().parent
ram_dir = this_dir.parent / 'build' / 'temp'
model_dir = Path(os.environ['OPENRAM_TECH']) / tech_name / 'models' / 'nom'

# determine the name of the SRAM
output_name = f'sram_{word_size}_{num_words}_{tech_name}'

# build up list of ports to connect
conn_ports = []
probe_ports = []
din0, addr0 = [], []
for k in range(word_size):
    conn_ports += [f'din0[{k}]']
    din0 += [VoltageSource(f'din0_{k}', conn_ports[-1])]
for k in range(addr_size):
    conn_ports += [f'addr0[{k}]']
    addr0 += [VoltageSource(f'addr0_{k}', conn_ports[-1])]
conn_ports += ['csb0', 'web0', 'clk0']
for k in range(word_size):
    conn_ports += [f'dout0[{k}]']
    probe_ports += [f'V({conn_ports[-1]})']
conn_ports += ['vdd', '0']

csb0 = VoltageSource('csb0')
web0 = VoltageSource('web0')
clk0 = VoltageSource('clk0')
vdd_src = VoltageSource('vdd')

t = Time()
expct = []

def write(addr, value):
    # setup data, address, and write enable
    for k in range(word_size):
        din0[k].put(vdd*((value>>k)&1), t.t)
    for k in range(addr_size):
        addr0[k].put(vdd*((addr>>k)&1), t.t)
    web0.put(0, t.t)
    t.incr(0.1*clk_per)
    # produce clock rising edge and obey hold time
    clk0.put(vdd, t.t)
    t.incr(0.5*clk_per)
    for k in range(word_size):
        din0[k].put(0, t.t)
    for k in range(addr_size):
        addr0[k].put(0, t.t)
    web0.put(vdd, t.t)
    # produce clock falling edge
    clk0.put(0, t.t)
    t.incr(0.4*clk_per)

# declare read function
def check(addr, value):
    # setup data, address, and write enable
    for k in range(addr_size):
        addr0[k].put(vdd*((addr>>k)&1), t.t)
    web0.put(vdd, t.t)
    t.incr(0.1*clk_per)
    # produce clock rising edge and obey hold time
    clk0.put(vdd, t.t)
    t.incr(0.5*clk_per)
    for k in range(addr_size):
        addr0[k].put(0, t.t)
    web0.put(vdd, t.t)
    # produce clock falling edge
    clk0.put(0, t.t)
    t.incr(0.4*clk_per)
    # check output
    expct.append([t.t, []])
    for k in range(word_size):
        expct[-1][-1].append(vdd*((value>>k)&1))

# initialize all voltages to zero
t.incr(5*clk_per)

# bring up supply while de-asserting write enable
vdd_src.put(vdd, t.t)
web0.put(vdd, t.t)
t.incr(5*clk_per)

# generate test data
stim = [(k, randint(0, (1<<word_size)-1))
        for k in range(num_words)]

# write data in a random order
shuffle(stim)
for addr, data in stim:
    write(addr, data)

# check data in a random order
shuffle(stim)
for addr, data in stim:
    check(addr, data)

t.incr(5*clk_per)

newline = '\n'
OUTPUT = f"""\
*
.include {model_dir / 'nmos.sp'}
.include {model_dir / 'pmos.sp'}
.include {ram_dir / (output_name + '.sp')}

X0 {' '.join(conn_ports)} {output_name}

{vdd_src.compile(t.t)}
{csb0.compile(t.t)}
{web0.compile(t.t)}
{clk0.compile(t.t)}
{newline.join(elem.compile(t.t) for elem in din0)}
{newline.join(elem.compile(t.t) for elem in addr0)}

.tran {t.t/1e3} {t.t} uic

.control
run
set filetype=binary
write
exit
.endc
.probe {' '.join(probe_ports)}
.end
"""

with open('test.sp', 'w') as f:
    f.write(OUTPUT)

with open('expct.p', 'wb') as f:
    pickle.dump(expct, f)