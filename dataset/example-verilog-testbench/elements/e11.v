// time unit/ time precision
`timescale 1ns/1ps

module tb;
    reg [99:0] a;
    reg [99:0] b;
    reg sel;

    wire [99:0] out;
    wire [99:0] out_gt;
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
        a = 100'd123;
        b = 100'd456;
        sel = 0;
        #10;
        check_output();

        a = 100'd123;
        b = 100'd456;
        sel = 1;
        #10;
        check_output();

        a = 100'hAAAAAAAAAAAAAAAAAAAAAAAAA;
        b = 100'h5555555555555555555555555;
        sel = 0;
        #10;
        check_output();

        sel = 1;
        #10;
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


