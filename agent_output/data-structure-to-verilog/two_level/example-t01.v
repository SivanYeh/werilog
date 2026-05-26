module Mod1(input in1, input in2, input in3, output out1);

  wire __1;

  assign __1 = ~(in1 ^ in2); // Xnor1
  assign out1 = __1 ^ in3;   // Xor1

endmodule