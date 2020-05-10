`timescale 1ns/1ps

module test;
    // I/O
    logic [((`WORD_SIZE)-1):0] din0;
    wire [((`WORD_SIZE)-1):0] dout0;
    logic [($clog2(`NUM_WORDS)-1):0] addr0;
    logic csb0;
    logic web0;
    logic clk0;
    logic vdd;
    logic gnd;

    `MODULE_NAME dut (
        .din0(din0),
        .dout0(dout0),
        .addr0(addr0),
        .csb0(csb0),
        .web0(web0),
        .clk0(clk0)
        `ifdef VAMS
            , .vdd(vdd)
            , .gnd(gnd)
        `endif
    );

    task write(
        input [($clog2(`NUM_WORDS)-1):0] addr,
        input [((`WORD_SIZE)-1):0] value
    );
        // setup data, address, and write enable
        din0 = value;
        addr0 = addr;
        web0 = 0;
        #((0.1*(`CLK_PER))*1s);

        // produce clock rising edge and obey hold time
        clk0 = 1;
        #((0.5*(`CLK_PER))*1s);
        din0 = 0;
        addr0 = 0;
        web0 = 1;

        // produce clock falling edge
        clk0 = 0;
        #((0.4*(`CLK_PER))*1s);
    endtask

    task check(
        input [($clog2(`NUM_WORDS)-1):0] addr,
        input [((`WORD_SIZE)-1):0] value
    );
        // setup data, address, and write enable
        addr0 = addr;
        web0 = 1;
        #((0.1*(`CLK_PER))*1s);

        // produce clock rising edge and obey hold time
        clk0 = 1;
        #((0.5*(`CLK_PER))*1s);
        addr0 = 0;
        web0 = 1;

        // produce clock falling edge
        clk0 = 0;
        #((0.4*(`CLK_PER))*1s);

        // check output
        if (!(dout0 === value)) begin
            $error("Output mismatch: dout0=%0d vs value=%0d", dout0, value);
        end
    endtask

    integer i, j, tmp;
    integer indices [`NUM_WORDS];

    task init_indices();
        // generate list of indices in increasing order
        for (i=0; i<(`NUM_WORDS); i=i+1) begin
            indices[i] = i;
        end
    endtask

    task shuffle_indices();
        // shuffle indices with Fisher-Yates
        // ref: https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
        for (i=(`NUM_WORDS)-1; i>=1; i=i-1) begin
            // pick a random number such that 0 <= j <= i
            j = $urandom % (i+1);

            // swap indices[i] and indices[j]
            tmp = indices[i];
            indices[i] = indices[j];
            indices[j] = tmp;
        end
    endtask

    integer write_data [`NUM_WORDS];
    initial begin
        // initialize all voltages to zero
        din0 = 0;
        addr0 = 0;
        csb0 = 0 ;
        web0 = 0;
        clk0 = 0;
        vdd = 0;
        gnd = 0;
        #((5.0*(`CLK_PER))*1s);

        //  bring up supply while de-asserting write enable
        vdd = 1;
        web0 = 1;
        #((5.0*(`CLK_PER))*1s);

        // determine a random write order
        init_indices();
        shuffle_indices();

        // Write data in a random order
        for (i=(`NUM_WORDS)-1; i>=1; i=i-1) begin
            write_data[indices[i]] = $urandom % (1<<(`WORD_SIZE));
            write(indices[i], write_data[indices[i]]);
        end

        // determine a random read order
        shuffle_indices();

        // check data in a random order
        for (i=(`NUM_WORDS)-1; i>=1; i=i-1) begin
            check(indices[i], write_data[indices[i]])
        end

        $finish;
    end

endmodule
