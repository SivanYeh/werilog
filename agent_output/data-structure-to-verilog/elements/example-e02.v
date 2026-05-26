module Mod1 (
  input a,
  input b,
  output out1
);

  nand Nand1 (out1, a, b);

endmodule