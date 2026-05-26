// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;
    reg b;
    reg sel1, sel2;

    wire out1, out2;
    wire out1_gt, out2_gt;
    gt_Mod1 circuit_gt(
        .a(a),
        .b(b),
        .sel_b1(sel1),
        .sel_b2(sel2),
        .out_assign(out1_gt),
        .out_always(out2_gt)
    );
    Mod1 circuit(
        .a(a),
        .b(b),
        .sel_b1(sel1),
        .sel_b2(sel2),
        .out_assign(out1),
        .out_always(out2)
    );

    integer i, fail;
    initial begin
        fail = 0;
        a  = 0; b = 0; sel1 = 0; sel2 = 0; #10;
        check_output();
        a  = 0; b = 0; sel1 = 0; sel2 = 1; #10;
        check_output();
        a  = 0; b = 0; sel1 = 1; sel2 = 0; #10;
        check_output();
        a  = 0; b = 0; sel1 = 1; sel2 = 1; #10;
        check_output();
        a  = 0; b = 1; sel1 = 0; sel2 = 0; #10;
        check_output();
        a  = 0; b = 1; sel1 = 0; sel2 = 1; #10;
        check_output();
        a  = 0; b = 1; sel1 = 1; sel2 = 0; #10;
        check_output();
        a  = 0; b = 1; sel1 = 1; sel2 = 1; #10;
        check_output();
        a  = 1; b = 0; sel1 = 0; sel2 = 0; #10;
        check_output();
        a  = 1; b = 0; sel1 = 0; sel2 = 1; #10;
        check_output();
        a  = 1; b = 0; sel1 = 1; sel2 = 0; #10;
        check_output();
        a  = 1; b = 0; sel1 = 1; sel2 = 1; #10;
        check_output();
        a  = 1; b = 1; sel1 = 0; sel2 = 0; #10;
        check_output();
        a  = 1; b = 1; sel1 = 0; sel2 = 1; #10;
        check_output();
        a  = 1; b = 1; sel1 = 1; sel2 = 0; #10;
        check_output();
        a  = 1; b = 1; sel1 = 1; sel2 = 1; #10;
        check_output();
        if (fail == 0) begin
            $display("Result : success");
        end else begin
           $display("Result : fail");
        end
        $finish;
    end

    task check_output;
        begin
            if (out1 === out1_gt && out2 === out2_gt) begin
                $display("a = %b, b = %b, sel_b1 = %b, sel_b2 = %b | PASS", a, b, sel1, sel2);
            end else begin
                fail = 1;
                $display("a = %b, b = %b, sel_b1 = %b, sel_b2 = %b | FAIL", a, b, sel1, sel2);
            end
        end
    endtask
endmodule


