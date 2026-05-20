module Transmitter (
    output wire out1
);
    assign out1 = 1'b1; // Constantly sends a high signal
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
    Transmitter Mod1 (
        .out1(intermediate_connection)
    );

    // 3. Instantiate the Receiver
    Receiver Mod2 (
        .in1(intermediate_connection),
        .out1(final_output)
    );

endmodule