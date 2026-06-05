// Module Mod1 definition
// This module has no specified operations and no inputs, but an output.
// A common interpretation for such a source module is to drive its output with a constant value.
// Here, we assign it to a logical high (1'b1).
module Mod1 (output out1);
    assign out1 = 1'b1;
endmodule

// Module Mod2 definition
module Mod2 (input in1, output out1);
    // The operation "invert" (described as "buffer with invert")
    // corresponds to a NOT gate in Verilog.
    not Inv1 (out1, in1);
endmodule

// Top_Level module definition
module Top_Level (output final_output);
    // Declare internal wires to connect outputs of sub-modules to inputs of others,
    // and eventually to the top-level output.
    wire w_mod1_out1;
    wire w_mod2_out1;

    // Instantiate Mod1
    // Connect Mod1's 'out1' port to the internal wire 'w_mod1_out1'.
    Mod1 mod1_inst (
        .out1(w_mod1_out1)
    );

    // Instantiate Mod2
    // Connect Mod2's 'in1' port to 'w_mod1_out1' (output of Mod1).
    // Connect Mod2's 'out1' port to the internal wire 'w_mod2_out1'.
    Mod2 mod2_inst (
        .in1(w_mod1_out1),
        .out1(w_mod2_out1)
    );

    // Connect Mod2's output ('w_mod2_out1') to the Top_Level's 'final_output' port.
    assign final_output = w_mod2_out1;

endmodule