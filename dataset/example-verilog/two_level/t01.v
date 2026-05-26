module gt_Mod1(input in1, input in2, input in3, output out1);
    wire int1;
    assign int1 = in1 ~^ in2;
    assign out1 = int1 ^ in3;
endmodule
