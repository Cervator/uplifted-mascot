# Windows Setup Guide

Windows-specific setup instructions for the Uplifted Mascot ingestion scripts.

## Common Windows Issues

### Issue: "Cannot find file specified" when installing packages

This happens when Windows locks executable files. Solutions:

**Solution 1: Use Virtual Environment (Recommended)**

```cmd
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Now install packages
pip install -r requirements.txt
```

**Solution 2: Install as User**

```cmd
pip install --user -r requirements.txt
```

**Solution 3: Close Python Processes**

1. Close all Python windows/IDEs
2. Open Task Manager (Ctrl+Shift+Esc)
3. End any Python processes
4. Try installing again

**Solution 4: Run as Administrator**

1. Right-click Command Prompt
2. Select "Run as administrator"
3. Navigate to your directory
4. Run pip install

**Solution 5: Force Reinstall**

```cmd
pip install --force-reinstall --no-cache-dir -r requirements.txt
```

## Step-by-Step Windows Setup

### 1. Create Virtual Environment

```cmd
cd D:\Dev\GitWS\bifrost
python -m venv um-venv
```

### 2. Activate Virtual Environment

```cmd
um-venv\Scripts\activate
```

You should see `(um-venv)` in your prompt.

### 3. Upgrade Pip

```cmd
python -m pip install --upgrade pip
```

### 4. Install Dependencies

For ingestion scripts:
```cmd
cd um\scripts
pip install -r requirements.txt
```

For RAG service:
```cmd
cd ..\rag-service
pip install -r requirements.txt
```

### 5. Verify Installation

```cmd
python -c "from google.cloud import aiplatform; print('OK')"
```

## Path Issues on Windows

### Using Paths in Scripts

Windows uses backslashes, but Python handles both. However, when passing paths as arguments:

```cmd
# Use forward slashes (works on Windows too)
python scripts/process_docs.py ../sample-md chunks.json

# Or use backslashes with quotes
python scripts\process_docs.py ..\sample-md chunks.json
```

### Environment Variables

Set environment variables in Command Prompt:
```cmd
set GCP_PROJECT_ID=your-project-id
```

Or in PowerShell:
```powershell
$env:GCP_PROJECT_ID="your-project-id"
```

For persistent environment variables, use System Properties or setx:
```cmd
setx GCP_PROJECT_ID "your-project-id"
```

## Troubleshooting

### "python is not recognized"

- Add Python to PATH during installation
- Or use full path: `C:\Python311\python.exe`

### "pip is not recognized"

- Use: `python -m pip` instead of just `pip`
- Or: `python.exe -m pip`

### Virtual Environment Not Activating

- Make sure you're in the right directory
- Check that `venv\Scripts\activate.bat` exists
- Try: `.\venv\Scripts\activate` (PowerShell)

### Permission Errors

- Run Command Prompt as Administrator
- Or install to user directory: `pip install --user`

## Quick Start Commands (Windows)

```cmd
# 1. Setup
cd D:\Dev\GitWS\bifrost
python -m venv um-venv
um-venv\Scripts\activate

# 2. Install
cd um\scripts
pip install -r requirements.txt

# 3. Authenticate
gcloud auth application-default login
set GCP_PROJECT_ID=your-project-id

# 4. Process
python process_docs.py ..\..\sample-md chunks.json

# 5. Create embeddings
python create_embeddings.py chunks.json embeddings.json
```

