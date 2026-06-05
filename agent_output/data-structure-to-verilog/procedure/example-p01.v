module Mod1 (
  input a,
  input b,
  output wire out_assign,
  output reg out_alwaysblock
);

  // Operation And1: and of a and b assigned to out_assign
  assign out_assign = a & b;

  // Operation And2: and of a and b assigned to out_alwaysblock via an always block
  always @(*) begin
    out_alwaysblock = a & b;
  end

endmodule