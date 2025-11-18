# IDE Setup for Uplifted Mascot

After installing dependencies in your virtual environment, configure your IDE to use it.

## VS Code

1. **Open Command Palette**: `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. **Select Python Interpreter**: Type "Python: Select Interpreter"
3. **Choose venv**: Select `.\venv\Scripts\python.exe` (or `./venv/bin/python` on Mac/Linux)

**Or** the workspace should auto-detect the venv if `.vscode/settings.json` exists (already created).

**Verify it's working:**
- Open any Python file (e.g., `scripts/create_embeddings.py`)
- Check the bottom-right corner of VS Code - it should show the Python version from your venv
- IDE warnings should disappear after a moment

## PyCharm

1. **File** → **Settings** (or `Ctrl+Alt+S`)
2. **Project** → **Python Interpreter**
3. Click the gear icon → **Add...**
4. Select **Existing environment**
5. Browse to: `D:\Dev\GitWS\uplifted-mascot\venv\Scripts\python.exe`
6. Click **OK**

**Verify it's working:**
- Check the bottom-right corner - should show your venv Python version
- IDE warnings should clear after indexing

## Other IDEs

- **Sublime Text**: Install "LSP-pyright" or "Anaconda" package, configure to use venv
- **Vim/Neovim**: Configure your LSP (pyright, pylsp, etc.) to use `venv/Scripts/python.exe`
- **Emacs**: Configure `python-shell-interpreter` to point to venv

## Verify Installation

Run this to verify all packages are installed:

```cmd
venv\Scripts\activate.bat
python -c "import chromadb; import vertexai; import fastapi; print('✓ All packages installed!')"
```

If you see errors, re-run the setup script or manually install:
```cmd
pip install -r scripts\requirements.txt
pip install -r rag-service\requirements.txt
pip install "importlib-metadata>=6.0.0" vertexai
```

