import sys
import decida.Data
import scipy.interpolate
import pickle

def check(predict, meas, abs_tol=0.1):
    if not (abs(predict-meas) <= abs_tol):
        print(f'Expected {predict} but got {meas}')

# read out arguments
word_size = int(sys.argv[4])

# read simulation result
data = decida.Data.Data()
data.read_nutmeg('out.raw')

time = data.get('time')
dout0 = [scipy.interpolate.interp1d(time, data.get(f'dout0[{k}]'))
         for k in range(word_size)]

# read expected result
with open('expct.p', 'rb') as f:
    expct = pickle.load(f)
print(expct)

# check results
for t, expct_vals in expct:
    for k in range(word_size):
        print(f'Checking dout0[{k}]({t})')
        check(expct_vals[k], dout0[k](t))