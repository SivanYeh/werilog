`timescale 1ns/1ps

module tb;

    wire out, out_gt;

    gt_Top_Level circuit_gt (
        .final_output(out_gt)
    );

    Top_Level circuit (
        .final_output(out)
    );

    integer fail;
    initial begin
        fail = 0;
        #10;
        check_output();
        if (fail == 0) begin
            $display("Result : success");
        end else begin
           $display("Result : fail");
        end
        $finish;

        $finish;
    end

    task check_output;
        begin
            if (out !== out_gt) begin
                fail = 1;
            end
        end
    endtask

endmodule
