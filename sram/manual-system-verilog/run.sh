# make the build directory
rm -rf build
mkdir -p build
cd build

# run Icarus Verilog
iverilog -o test -g2012 -f ../iverilog.f \
    -DNUM_WORDS=$3 -DWORD_SIZE=$4 \
    -DVDD=$5 -DCLK_PER=$6 -DMODULE_NAME="sram_$4_$3_$7" \
    ../../build/temp/*.v ../test.sv \
    && vvp -N test