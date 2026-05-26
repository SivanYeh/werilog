// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;
    reg b;
    reg sel;

    wire out;
    wire out_gt;
    gt_Mod1 circuit_gt(
        .in1(a),
        .in2(b),
        .sel1(sel),
        .out1(out_gt)
    );
    Mod1 circuit(
        .in1(a),
        .in2(b),
        .sel1(sel),
        .out1(out)
    );

    integer i, fail;
    initial begin
        fail = 0;
        a  = 0; b = 0; sel = 0; #10;
        check_output();

        a  = 0; b = 0; sel = 1; #10;
        check_output();

        a  = 0; b = 1; sel = 0; #10;
        check_output();

        a  = 0; b = 1; sel = 1; #10;
        check_output();

        a  = 1; b = 0; sel = 0; #10;
        check_output();

        a  = 1; b = 0; sel = 1; #10;
        check_output();

        a  = 1; b = 1; sel = 0; #10;
        check_output();

        a  = 1; b = 1; sel = 1; #10;
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
            if (out_gt !== out) begin
                fail = 1;
                $display("in1 = %b, in2 = %b, sel1 = %b | FAIL", a, b, sel);
            end else begin
                $display("in1 = %b, in2 = %b, sel1 = %b | PASS", a, b, sel);
            end
        end
    endtask
endmodule


