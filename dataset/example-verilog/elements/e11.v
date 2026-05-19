module Mod1( 
    input [99:0] in1, in2, 
    input sel,
    output [99:0] out); 
	assign out = sel?b:a;
endmodule
