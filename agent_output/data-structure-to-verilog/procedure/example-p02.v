module Mod1 (
    input a,
    input b,
    input sel_b1,
    input sel_b2,
    output out_assign,
    output reg out_always
);

    // Internal wires for intermediate results
    wire __1;
    wire __2;

    // And1: __1 = sel_b1 AND sel_b2
    assign __1 = sel_b1 & sel_b2;

    // And2: __2 = sel_b1 AND sel_b2
    assign __2 = sel_b1 & sel_b2;

    // Mux1: out_assign based on __1
    // If __1 is 0, select 'a'. If __1 is 1, select 'b'.
    assign out_assign = (__1 == 1'b1) ? b : a;

    // Mux2: out_always based on __2
    // If __2 is 0, select 'a'. If __2 is 1, select 'b'.
    always @(*) begin
        if (__2 == 1'b1) begin
            out_always = b;
        end else begin
            out_always = a;
        end
    end

endmodule