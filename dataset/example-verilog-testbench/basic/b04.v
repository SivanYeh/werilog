// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg a;
    reg b;
    reg c;

    wire out1, out2, out3, out4;
    wire out1_gt, out2_gt, out3_gt, out4_gt;
    Mod1 circuit(
        .in1(a),
        .in2(b),
        .in3(c),
        .out1(out1),
        .out2(out2),
        .out3(out3),
        .out4(out4)
    );
    gt_Mod1 circuit_gt(
        .in1(a),
        .in2(b),
        .in3(c),
        .out1(out1_gt),
        .out2(out2_gt),
        .out3(out3_gt),
        .out4(out4_gt)
    );

    integer i, fail;
    initial begin
        fail = 0;
        a  = 0; b = 0; c = 0; #10;
        check_output();

        a  = 0; b = 0; c = 1; #10;
        check_output();

        a  = 0; b = 1; c = 0; #10;
        check_output();

        a  = 0; b = 1; c = 1; #10;
        check_output();
        
        a  = 1; b = 0; c = 0; #10;
        check_output();
        
        a  = 1; b = 0; c = 1; #10;
        check_output();

        a  = 1; b = 1; c = 0; #10;
        check_output();

        a  = 1; b = 1; c = 1; #10;
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
            if (out1 === out1_gt && out2 === out2_gt && out3 === out3_gt && out4 === out4_gt) begin
                $display("in1 = %b, in2 = %b, in3 = %b | PASS", a, b ,c);
            end else begin
                fail = 1;
                $display("in1 = %b, in2 = %b, in3 =  %b | FAIL", a, b ,c);
            end
        end
    endtask
endmodule


