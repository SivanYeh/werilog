module Mod1 (
    input in1,
    input in2,
    output out1,
    output out2,
    output out3,
    output out4,
    output out5,
    output out6,
    output out7
);

    wire __1; // Declare the intermediate signal

    // Gate instantiations
    and (out1, in1, in2);
    or (out2, in1, in2);
    xor (out3, in1, in2);
    nand (out4, in1, in2);
    nor (out5, in1, in2);
    xnor (out6, in1, in2);
    not (__1, in2); // Invert gate, output __1 from input in2
    and (out7, in1, __1); // And gate with in1 and __1 producing out7

endmodule