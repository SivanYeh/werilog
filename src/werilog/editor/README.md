# Werilog Local Diagram Editor

This package provides the local Tkinter-based dual editor for the Werilog project, translating Verilog code backwards into interactive visual diagrams.

## UI Layout
- **Right panel**: Verilog source code view
- **Left panel**: Interactive Diagram rendered from the parsed Verilog

## Architecture

The editor is integrated into the main `werilog` package structure under `src/werilog/editor/`:
- **`tk_app.py`**: Main application logic for the Tkinter desktop editor.
- **`extractverilog.py`**: Extracts Verilog into class objects (Module with ports, elements like logic gates, muxes, etc.) and exports to JSON. Uses the Factory Method for module creation and the Composition pattern for modeling modules and their combinations.
- **`draw_strategy.py`**: Encapsulates (Strategy pattern) how wires are drawn (orthogonal square routing and jump wires over intersections).
- **`error_detector.py`**: Real-time syntax error checking while typing.
- **`../agent/autocomplete.py`**: LLM agent backend used for inline code suggestions.

Assets (SVGs, Verilog examples) are now read natively from the project's `dataset/` directory.

## Usage

### 1. Install Dependencies

Install and sync the required Python packages using `uv`:

```bash
uv sync
```

### 2. Configure the LLM Agent (Optional)

To enable AI code suggestions in the desktop editor, configure a lightweight LLM backend (e.g., Qwen).

1. Edit the `inference` section in `config.yaml` (at the project root):
   ```yaml
   inference:
     backend: "huggingface" # options: "huggingface" or "ollama"
     model: "Qwen/Qwen2.5-Coder-1.5B"
   ```
2. If using HuggingFace, copy `.env.example` to `.env` and insert your API key:
   ```bash
   cp .env.example .env
   # Edit .env to add HUGGINGFACE_API_KEY
   ```

### 3. Run the Desktop Editor UI

To run the interactive desktop editor from the project root:

```bash
uv run python main.py editor
```

**Editor Features:**
- **Code Suggestions**: Pause typing for 500ms to receive an inline AI suggestion (highlighted in gray/green).
- Press `<Tab>` to accept the suggestion.
- Press `<Escape>` to reject it.

## Testing

The test suite has been moved to the top-level `tests/` directory. Run them from the project root:

### 1. Test Wire Routing Strategies
To verify the `SquareWireStrategy`, `StraightWireStrategy`, and `JumpWireStrategy` routing logic:

```bash
# Headless assertion checks
PYTHONPATH=src uv run python tests/test_draw_strategy.py

# Launch Tkinter visualization window
PYTHONPATH=src uv run python tests/test_draw_strategy.py --window
```

### 2. Test Verilog Module Extraction
To verify Verilog syntax parsing and object model extraction on sample flat modules:

```bash
PYTHONPATH=src uv run python tests/test_b02_b04.py
```