# Knowledge Base Setup

## Overview

The Knowledge Base is the source of truth for the Uplifted Mascot system. It consists of markdown documentation files stored in GitHub repositories that will be processed and embedded into the vector database.

## Requirements

- GitHub repository with markdown files
- Access to clone the repository
- Python 3.9+ for processing scripts
- Basic understanding of markdown structure

## Repository Structure

### Recommended Structure

```
your-repo/
├── README.md
├── docs/
│   ├── overview.md
│   ├── getting-started.md
│   └── api-reference.md
├── guides/
│   ├── installation.md
│   └── configuration.md
└── specs/
    └── protocol-v1.md
```

### File Naming Conventions

- Use lowercase with hyphens: `getting-started.md`
- Avoid spaces in filenames
- Group related content in directories
- Keep README.md at root for project overview

## Supported Content Types

### Primary: Markdown Files

- `.md` files (Markdown)
- `.markdown` files
- Files with markdown content

### Content Guidelines

**Good Content**:
- Clear headings and structure
- Complete sentences and paragraphs
- Code examples where relevant
- Links to related documentation

**Avoid**:
- Binary files (images should be referenced, not embedded)
- Very short files (< 100 characters) - these may not embed well
- Duplicate content across multiple files

## Manual Setup

### Step 1: Clone Repository

```bash
# Create a working directory
mkdir -p ~/um-workspace
cd ~/um-workspace

# Clone your repository
git clone https://github.com/your-org/your-docs-repo.git
cd your-docs-repo

# Verify markdown files are present
find . -name "*.md" -type f | head -10
```

### Step 2: Verify Repository Access

```bash
# Check repository structure
ls -la

# Count markdown files
find . -name "*.md" -type f | wc -l

# View a sample file to verify content
head -20 README.md
```

### Step 3: Prepare for Processing

Create a configuration file to specify which files to process:

```bash
# Create config directory
mkdir -p ~/um-workspace/config

# Create a simple file list (we'll automate this later)
cat > ~/um-workspace/config/repo-config.json << EOF
{
  "repository": "your-org/your-docs-repo",
  "local_path": "~/um-workspace/your-docs-repo",
  "include_patterns": ["*.md"],
  "exclude_patterns": [
    "node_modules/**",
    ".git/**",
    "**/CHANGELOG.md"
  ],
  "min_file_size": 100
}
EOF
```

## Multiple Repositories

You can process multiple repositories for different projects:

### Example: Demicracy + Bifrost

```bash
# Clone both repositories
cd ~/um-workspace
git clone https://github.com/your-org/demicracy-docs.git
git clone https://github.com/your-org/bifrost.git

# Verify both
ls -d */
```

### Configuration for Multiple Repos

```json
{
  "repositories": [
    {
      "name": "demicracy",
      "path": "~/um-workspace/demicracy-docs",
      "mascot": "bill"
    },
    {
      "name": "bifrost",
      "path": "~/um-workspace/bifrost",
      "mascot": "gooey"
    }
  ]
}
```

## File Filtering

### Include Only Specific Directories

```bash
# Example: Only process docs/ directory
find ~/um-workspace/your-repo/docs -name "*.md" -type f
```

### Exclude Patterns

Common exclusions:
- `CHANGELOG.md` - Usually too verbose
- `LICENSE.md` - Not useful for Q&A
- `node_modules/` - Dependencies
- `.git/` - Version control

## Validation

### Check File Quality

```bash
# Find very small files (may not be useful)
find . -name "*.md" -type f -size -100c

# Find very large files (may need special handling)
find . -name "*.md" -type f -size +100k

# Check for empty files
find . -name "*.md" -type f -empty
```

### Verify Markdown Structure

```bash
# Count headings (good structure indicator)
grep -r "^#" . --include="*.md" | wc -l

# Find files with no headings (may be less useful)
for file in $(find . -name "*.md"); do
  if ! grep -q "^#" "$file"; then
    echo "No headings: $file"
  fi
done
```

## Next Steps

Once your knowledge base is set up:

1. **Verify files are accessible** - All markdown files should be readable
2. **Check repository size** - Large repos may take longer to process
3. **Proceed to Ingestion** - See `02-ingestion.md` for processing steps

## Troubleshooting

### Issue: Repository is Private

**Solution**: Use SSH keys or personal access tokens
```bash
# SSH (if configured)
git clone git@github.com:your-org/your-repo.git

# HTTPS with token (set as environment variable)
export GITHUB_TOKEN=your_token_here
git clone https://${GITHUB_TOKEN}@github.com/your-org/your-repo.git
```

### Issue: Too Many Files

**Solution**: Use `.gitignore`-style patterns to filter
```bash
# Process only specific directories
find docs/ guides/ -name "*.md" -type f
```

### Issue: Files Have Special Characters

**Solution**: Ensure UTF-8 encoding
```bash
# Check encoding
file -i your-file.md

# Convert if needed (example for ISO-8859-1)
iconv -f ISO-8859-1 -t UTF-8 your-file.md > your-file-utf8.md
```

## Manual File List Generation

For initial testing, create a simple file list:

```bash
# Generate list of markdown files
find ~/um-workspace/your-repo -name "*.md" -type f > ~/um-workspace/file-list.txt

# Review the list
cat ~/um-workspace/file-list.txt

# Count files
wc -l ~/um-workspace/file-list.txt
```

This file list will be used in the next step (Ingestion) to process the documents.

