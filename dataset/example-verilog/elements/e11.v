module Mod1( 
    input [99:0] in1,
    input [99:0] in2, 
    input sel1,
    output [99:0] out1); 
	assign out1 = sel1?in2:in1;
endmodule
