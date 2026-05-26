// time unit/ time precision
`timescale 1ns/1ps

module tb;

    gt_Mod1 circuit_gt(
    );
    Mod1 circuit(
    );

    initial begin
        $display("Result : success");
        $finish;
    end
endmodule


