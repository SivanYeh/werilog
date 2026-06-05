// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;

    wire out;
    wire out_gt;
    gt_Mod1 circuit_gt(
        .a(a),
        .out1(out_gt)
    );
    Mod1 circuit(
        .a(a),
        .out1(out)
    );

    integer i, fail;
    initial begin
        fail = 0;
        a  = 0; #10;
        check_output();

        a = 1; #10;
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
                $display("out = %b | FAIL", a);
            end else begin
                $display("out = %b | PASS", a);
            end
        end
    endtask
endmodule


