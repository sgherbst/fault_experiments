# make the build directory
rm -rf build
mkdir -p build
cd build

# generate testbench
python ../preprocess.py "$@"

# run testbench
ngspice -b test.sp -r out.raw

# analyze results
python ../postprocess.py "$@"
