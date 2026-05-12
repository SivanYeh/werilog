# Bidirectional HDL & Diagram Editor

A prototype for a real-time bidirectional editor for Hardware Description Language (HDL) and visual block diagrams.

## Features (Prototype)

- **Bidirectional Synchronization**: Synchronizes changes between the visual diagram and HDL code.
- **Visual Editing**: Basic block dragging and wiring between ports.
- **Code Parsing**: Simple regex-based parsing to update the diagram from text.


## Prerequisites

- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Python 3.11+

## Getting Started

### 1. Setup Environment
Use the provided script to initialize the project and install dependencies:
```bash
bash uv-init.sh
```

### 2. Run the Editor
Launch the application using `uv`:
```bash
uv run main.py
```

## How to Use

1. **Move Blocks**: Click and drag the blue module block to reposition it.
2. **Draw Wires**: Click on a port (yellow dot) and drag to another port to create a connection.
3. **Edit Code**: Type in the right-hand panel. For example:
   - Add `assign out = in;` to create a wire visually.
   - Remove the `module` definition to hide the block.
