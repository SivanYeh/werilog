module Mod1( 
    input in1, in2, sel1,
    output out1 ); 
	assign out1 = sel1?in2:in1;
endmodule
