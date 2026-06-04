# Werilog
Currently my AICG final project, hoping it becomes a powerful open-source tool with team work :)

## Description
Werilog(Web Verilog) is a browser-based environment for Hardware Description Languages (HDL) designed to lower the barrier to hardware design. By integrating Icarus Verilog into a web interface, we’re removing the "local environment tax" for students and devs.

In a traditional setup, writing a core component like a RISC-V Program Counter requires a complex toolchain. In Werilog, you can define it instantly.

Use the simplest module [Add PC] for example:
```Verilog
module program_counter (
    input wire clk, reset,
    output reg [31:0] pc
);
    always @(posedge clk) begin
        if (reset) pc <= 32'h0;
        else       pc <= pc + 32'd4; // Move to next instruction
    end
endmodule
```
Werilog will generate the diagram for the module:
![alt text](./img/in_progress.png)

Key Features:
- Diagram View: Live visualization of HDL code into interactive logic schematics.
- Assembly View: A dedicated RISC-V inspector to bridge the gap between RTL and software.
- Zero-Setup Simulation: Run iverilog directly in the browser via WebAssembly.
- AI Agent: Import AI Agent so XPU(eg CPU, GPU, NPU, TPU) design can be semiautomative. (Added on 3/13/2026 after discussion with Prof. Ouhyoung and Prof. Cheng)

## How to Run

### Local Diagram Editor
The project includes a local desktop prototype for the Verilog Diagram Editor using Tkinter. 
To launch it, simply run:
```bash
uv run python main.py editor
```
For more details, see the editor's [README](src/werilog/editor/README.md).

### WebGL Web Application
The project also includes a browser-based WebGL application that visualizes the circuits dynamically.
To launch the backend server and web UI, run:
```bash
uv run python main.py webapp
```
Then navigate to `http://127.0.0.1:8000` in your browser.
For more detailed information on its architecture and tests, see the webapp's [README](src/werilog/webapp/README.md).

References:
- for verilog:
https://github.com/steveicarus/iverilog
- for assembly:
https://www.cs.cornell.edu/courses/cs3410/2019sp/riscv/interpreter/
- for knowledge:
Patterson, D. A., Hennessy, J. L. (2020). Computer Organization and Design RISC-V Edition: The Hardware Software Interface. Netherlands: Morgan Kaufmann.