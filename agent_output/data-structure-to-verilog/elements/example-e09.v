module Mod1(input a, input b, output out1);

  wire __1;

  not Inv1(__1, b);
  and And1(out1, a, __1);

endmodule