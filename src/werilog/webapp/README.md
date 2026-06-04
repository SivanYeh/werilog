# Werilog Web Application

This module provides the browser-based WebGL interface for the Werilog hardware design environment. It bridges the core Verilog AST parsing and routing logic (from `werilog.editor`) with a modern, interactive web frontend powered by Pixi.js and Monaco Editor.

## Architecture

The webapp is built with a decoupled client-server architecture:

- **Backend (`server.py`)**: A FastAPI server that exposes REST endpoints for the frontend.
  - `/api/parse`: Parses raw Verilog code sent from the frontend, runs it through the AST extraction and hierarchical routing engine, and returns a JSON layout structure describing the modules, elements, ports, and wire paths.
  - `/api/suggest`: Integrates with `werilog.agent.core` to provide AI-powered auto-completion using Ollama or HuggingFace inference backends based on the current context and syntax errors.
- **Frontend (`static/`)**:
  - `index.html`: The main entry point containing the editor pane, UI controls (AI Chat, Export), and the WebGL canvas.
  - `main.js`: Handles the Pixi.js canvas rendering, interactive wiring, dragging/resizing logic, communication with the backend APIs, and exporting the logic schematic as SVG vectors.

## How to Run

From the root of the repository, start the backend server via the CLI:
```bash
uv run python main.py webapp
```

This will spin up a `uvicorn` instance serving both the REST APIs and the static frontend assets on `http://127.0.0.1:8000`. Navigate to that URL in a modern web browser to start designing.

## Testing

The webapp includes both backend and headless UI tests located in `tests/webapp/`.

### Backend Tests
Validates the FastAPI REST endpoints (`/api/parse` and `/api/suggest`).
```bash
uv run pytest tests/webapp/test_api.py
```

### Frontend UI Tests
Simulates a real headless Chromium browser session to verify that the Monaco editor connects, the logic parses correctly into the WebGL renderer, and layout diagrams are correctly updated.
```bash
uv run python tests/webapp/check_chrome.py
```
*(Requires Playwright browsers to be installed via `uv run playwright install chromium`)*

## Features
- **Live Auto-Rendering**: Code modifications are debounced and instantly visualized on the WebGL canvas.
- **Agent Integration**: Seamless inline AI suggestions based on code logic and current synthesis errors.
- **Vector Exporting**: Users can export the generated interactive diagrams accurately to `.svg` formats for external reporting and documentation.
