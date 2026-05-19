module Transmitter (
    output wire data_out
);
    assign data_out = 1'b1; // Constantly sends a high signal
endmodule

module Receiver(
    input wire data_in,
    output wire result
);
    assign result = ~data_in; // Inverts the received signal
endmodule

module Top_Level (
    output wire final_output
);

    // 1. Declare a wire to carry the signal between modules
    wire intermediate_connection;

    // 2. Instantiate the Transmitter
    // Syntax: ModuleName InstanceName (.port_name(signal_name))
    Transmitter u1 (
        .data_out(intermediate_connection)
    );

    // 3. Instantiate the Receiver
    Receiver u2 (
        .data_in(intermediate_connection),
        .result(final_output)
    );

endmodule