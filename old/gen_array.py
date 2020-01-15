from pathlib import Path
THIS_DIR = Path(__file__).resolve().parent

def gen_sram_array(fname, n_row, n_col, bit_name='sram_bit', arr_name='sram_array', nl='\n'):
    lines = []

    lines += ['* Generate SPICE code for SRAM row', '']

    # build up pin list for module
    decl = ['.subckt', arr_name, 'vdd', 'vss']
    for row in range(n_row):
        decl += [f'wl<{row}>']
    for col in range(n_col):
        decl += [f'lbl<{col}>', f'lblb<{col}>']
    lines += [' '.join(decl)]

    # declare module body
    for row in range(n_row):
        for col in range(n_col):
            idx = (row * n_col) + col
            lines += [f'X{idx} lbl<{col}> lblb<{col}> vdd vss wl<{row}> {bit_name}']

    # end the subcircuit definition
    lines += ['.ends']

    with open(fname, 'w') as f:
        f.write(nl.join(lines))

if __name__ == '__main__':
    fname = THIS_DIR / 'sram_array.sp'
    gen_sram_array(fname=fname, n_row=4, n_col=8)
