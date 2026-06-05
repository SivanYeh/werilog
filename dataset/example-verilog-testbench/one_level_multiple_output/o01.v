// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;
    reg b;

    wire out1, out2, out3, out4, out5, out6 ,out7;
    wire out1_gt, out2_gt, out3_gt, out4_gt, out5_gt, out6_gt ,out7_gt;
    gt_Mod1 circuit_gt(
        .in1(a),
        .in2(b),
        .out1(out1_gt),
        .out2(out2_gt),
        .out3(out3_gt),
        .out4(out4_gt),
        .out5(out5_gt),
        .out6(out6_gt),
        .out7(out7_gt)
    );
    Mod1 circuit(
        .in1(a),
        .in2(b),
        .out1(out1),
        .out2(out2),
        .out3(out3),
        .out4(out4),
        .out5(out5),
        .out6(out6),
        .out7(out7)
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
            if (out1_gt === out1 && out2_gt === out2 && out3_gt === out3 && out4_gt === out4 && out5_gt === out5 && out6_gt === out6 && out7_gt === out7) begin
                $display("in1 = %b, in2 = %b | PASS", a, b);
            end else begin
                fail = 1;
                $display("in1 = %b, in2 = %b | FAIL", a, b);
            end
        end
    endtask
endmodule


