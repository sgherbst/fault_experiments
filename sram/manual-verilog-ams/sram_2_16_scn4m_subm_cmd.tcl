database -open -vcd vcddb -into waveforms.vcd -default -timescale ps
probe -create -all -vcd -depth all
run 10000ns
quit