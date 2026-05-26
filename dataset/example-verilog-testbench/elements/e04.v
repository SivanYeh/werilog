// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;
    reg b;

    wire out;
    wire out_gt;
    gt_Mod1 circuit_gt(
        .a(a),
        .b(b),
        .out1(out_gt)
    );
    Mod1 circuit(
        .a(a),
        .b(b),
        .out1(out)
    );

    integer i, fail;
    initial begin
        fail = 0;
        a  = 0; b = 0; #10;
        check_output();

        a = 0; b = 1; #10;
        check_output();

        a = 1; b = 0; #10;
        check_output();

        a = 1; b = 1; #10;
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
                $display("a = %b, b = %b | FAIL", a, b);
            end else begin
                $display("a = %b, b = %b | PASS", a, b);
            end
        end
    endtask
endmodule


