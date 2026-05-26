module gt_Mod1 (input a, input b, output out1);
    wire int1;
    assign int1 = ~b;
    assign out1 = a & int1;
endmodule
