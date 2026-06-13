import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from werilog.agent.core import VerilogAgent

def main():
    parser = argparse.ArgumentParser(description="Werilog CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Existing default agent test command (from old main)
    agent_parser = subparsers.add_parser("agent", help="Test the AI agent")
    
    # New editor command
    editor_parser = subparsers.add_parser("editor", help="Launch the Verilog Diagram Editor")
    
    # New webapp command
    webapp_parser = subparsers.add_parser("webapp", help="Launch the Verilog WebGL Application")
    
    args = parser.parse_args()

    if args.command == "editor":
        print("Launching Verilog Diagram Editor...")
        from werilog.editor.tk_app import HDLEditorApp
        app = HDLEditorApp()
        app.mainloop()
    elif args.command == "webapp":
        print("Launching Verilog WebGL Application on http://127.0.0.1:8000 ...")
        import uvicorn
        uvicorn.run("werilog.webapp.server:app", host="127.0.0.1", port=8000, reload=False)
    elif args.command == "agent" or not args.command:
        print("Initializing AI Agent for Verilog Autocomplete (FR5)...")
        agent = VerilogAgent()
        print("Agent ready! (API Engine not yet connected)")
        if not args.command:
            print("\nHint: Run `python main.py editor` to launch the GUI.")
            
if __name__ == "__main__":
    main()
