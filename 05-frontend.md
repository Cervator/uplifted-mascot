# Web Frontend

## Overview

The web frontend provides a simple, embeddable chat interface for the Uplifted Mascot. Users can ask questions and receive AI-powered responses from the RAG service.

## Prerequisites

- RAG service running and accessible (see `04-rag-service.md`)
- Basic HTML/JavaScript knowledge
- Web server (or use GitHub Pages for hosting)

## Simple HTML Interface

### Step 1: Copy Frontend Files

The frontend files are located in the `frontend/` directory of this repository.

**Copy the frontend directory:**
```bash
# Copy frontend directory
cp -r um/frontend ~/um-workspace/
# On Windows PowerShell:
xcopy /E /I um\frontend %USERPROFILE%\um-workspace\frontend
```

The main files are:
- `um/frontend/index.html` - Full page chat interface with modern styling
- `um/frontend/widget.html` - Compact embeddable widget version

Both files are complete, self-contained HTML files with embedded CSS and JavaScript. They include:
- Chat interface with message bubbles
- API integration with the RAG service
- Error handling and loading states
- Responsive design

### Step 2: Test Locally

```bash
# If RAG service is running on localhost:8000
# Open index.html in a browser
# Or use a simple HTTP server:

cd ~/um-workspace/frontend
python3 -m http.server 8080

# Then visit http://localhost:8080
```

## Embeddable Widget Version

### Step 3: Widget Version

The widget version is available at `um/frontend/widget.html`. It's a compact, minimal version designed for embedding in existing websites. The widget is 400x500px and includes all necessary functionality in a single HTML file.

## Configuration

### Step 4: Update Service URL

Before deploying, update the RAG service URL:

```javascript
// In index.html or widget.html, change:
const RAG_SERVICE_URL = 'http://YOUR_SERVICE_IP_OR_DOMAIN';
// Or for GKE:
const RAG_SERVICE_URL = 'http://YOUR_GKE_SERVICE_EXTERNAL_IP';
```

## Deployment Options

### Option 1: GitHub Pages

```bash
# Create gh-pages branch
cd ~/um-workspace/frontend
git init
git add index.html widget.html
git commit -m "Initial frontend"
git branch -M main
git remote add origin https://github.com/your-org/um-frontend.git
git push -u origin main

# Enable GitHub Pages in repository settings
# Point to main branch / root directory
```

### Option 2: Static Hosting (GCS)

```bash
# Create bucket
gsutil mb -p $GCP_PROJECT_ID gs://um-frontend

# Upload files
gsutil cp -r ~/um-workspace/frontend/* gs://um-frontend/

# Make public
gsutil iam ch allUsers:objectViewer gs://um-frontend

# Access at: http://storage.googleapis.com/um-frontend/index.html
```

### Option 3: Serve from GKE

For serving from GKE, you can create a simple nginx-based deployment that serves the static HTML files. The frontend files can be packaged in a container or served via a ConfigMap. See your Kubernetes documentation for serving static files.

## Manual Testing Workflow

```bash
# 1. Ensure RAG service is running
# Check: http://localhost:8000/health

# 2. Update frontend config
# Edit index.html, set RAG_SERVICE_URL

# 3. Serve frontend locally
cd ~/um-workspace/frontend
python3 -m http.server 8080

# 4. Open browser
# Visit: http://localhost:8080

# 5. Test questions:
# - "What is Bifrost?"
# - "How does JEP work?"
# - "Tell me about Terasology"
```

## Customization

### Change Mascot

```javascript
// In the HTML file, change:
const MASCOT = 'bill';  // Change from 'gooey' to 'bill'
const PROJECT = 'demicracy';  // Update project too
```

### Styling

Modify the CSS in the `<style>` section to match your project's branding.

## Troubleshooting

### Issue: CORS Errors

**Solution**: The RAG service already includes CORS middleware (see `um/rag-service/rag_service.py`). If you need to restrict origins, edit the `allow_origins` list in the CORS middleware configuration.

### Issue: Service Not Reachable

**Check**:
- RAG service is running
- Service URL is correct
- Firewall rules allow traffic
- For GKE: Service has external IP

### Issue: Slow Responses

**Optimize**:
- Reduce `top_k` in requests
- Add loading indicators
- Implement response caching

## Next Steps

Once the frontend is working:

1. **Customize styling** - Match your project's branding
2. **Add more features** - Conversation history, source links, etc.
3. **Deploy publicly** - Make it accessible to your community
4. **Gather feedback** - Improve based on user questions

## Complete Manual Workflow

```bash
# 1. Setup
cd ~/um-workspace/frontend
# Edit index.html: Update RAG_SERVICE_URL

# 2. Test locally
python3 -m http.server 8080
# Visit http://localhost:8080

# 3. Deploy (choose one):
# - GitHub Pages
# - GCS static hosting
# - Your own web server
```

## Integration Example

To embed in an existing website:

```html
<!-- Add to your website -->
<iframe 
    src="http://your-frontend-url/widget.html" 
    width="400" 
    height="500"
    frameborder="0"
    style="border-radius: 10px;">
</iframe>
```

Or use the full page version and link to it from your site.

