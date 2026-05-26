module Mod1 (
    input in1,
    input in2,
    input sel1,
    output out1
);

    // Mux1 logic:
    // If sel1 is high, output in2.
    // If sel1 is low, output in1.
    assign out1 = sel1 ? in2 : in1;

endmodule