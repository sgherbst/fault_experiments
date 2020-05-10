# make the build directory
rm -rf build
mkdir -p build
cd build

# run Icarus Verilog or Xcelium depending on the target
if [ "$1" == "verilog-ams" ]; then
    echo "tranSweep tran stop=1s" >> amscf.scs
    echo "amsd {"  >> amscf.scs
    echo "    ie vsup=$5 rout=1" >> amscf.scs
    echo "    config cell=sram_$4_$3_$7 use=spice" >> amscf.scs
    echo "    portmap subckt=sram_$4_$3_$7 autobus=yes busdelim=\"[]\"" >> amscf.scs
    echo "}" >> amscf.scs
    irun -modelpath "$OPENRAM_TECH/scn4m_subm/models/nom/nmos.sp" \
         -modelpath "$OPENRAM_TECH/scn4m_subm/models/nom/pmos.sp" \
         -modelpath ../../build/temp/*.sp -timescale 1ns/1ps \
         +define+NUM_WORDS=$3 +define+WORD_SIZE=$4 +define+VDD=$5 \
         +define+CLK_PER=$6 +define+MODULE_NAME="sram_$4_$3_$7" \
         +define+VAMS ../../build/temp/*.v ../test.sv amscf.scs
else
    iverilog -o test -g2012 -f ../iverilog.f \
        -DNUM_WORDS=$3 -DWORD_SIZE=$4 \
        -DVDD=$5 -DCLK_PER=$6 -DMODULE_NAME="sram_$4_$3_$7" \
        ../../build/temp/*.v ../test.sv \
        && vvp -N test
fi

