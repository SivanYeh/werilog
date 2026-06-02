module Transmitter (
    output out1
);

    assign out1 = 1'b1;

endmodule

module Receiver (
    input data_in,
	input data_in2,
    output result
);

    assign result = data_in& data_in2;

endmodule

module Top_Level (
    output final_output
);
	wire intermediate_connection;
    wire c2;
	
    Transmitter Mod1 (
            .out1(intermediate_connection)
        );
	Transmitter Mod3(.out1(c2));

    Receiver Mod2 (
            .data_in(intermediate_connection),
.data_in2(c2),
            .result(final_output)
        );

endmodule