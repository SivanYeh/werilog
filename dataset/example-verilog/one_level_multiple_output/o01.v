module top_module( 
    input in1, input in2,
    output out1,
    output out2,
    output out3,
    output out4,
    output out5,
    output out6,
    output out7,
);
    assign out1 = in1 & in2;
    assign out2 = in1 | in2;
    assign out3 = in1 ^ in2;
    assign out4 = ~(in1 & in2);
    assign out5 = ~(in1 | in2);
    assign out6 = ~(in1 ^ in2);
    assign out7 = in1 & (~in2);

endmodule
