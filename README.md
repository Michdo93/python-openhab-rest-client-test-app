# python-openhab-rest-client-test-app

Interactive test application for [python-openhab-rest-client](https://github.com/Michdo93/python-openhab-rest-client).

**Live Demo:** https://michdo93.github.io/python-openhab-rest-client-test-app/

---

## Architecture

```
Browser (GitHub Pages)
        │  fetch (HTTPS)
        ▼
Flask Backend (Render.com)
        │  python-openhab-rest-client
        ▼
myopenhab.org  ──►  openHAB (home)
```

- **Frontend** – pure static HTML/JS, hosted on GitHub Pages (no build step)
- **Backend** – Flask + gunicorn on Render.com (free tier), uses `python-openhab-rest-client`
- **openHAB** – reached via [myopenhab.org](https://myopenhab.org) cloud connector, or any other public URL

---

## Setup

### 1. Fork / Clone

```bash
git clone https://github.com/Michdo93/python-openhab-rest-client-test-app.git
cd python-openhab-rest-client-test-app
```

### 2. Deploy Backend to Render.com

1. Create a free account at [render.com](https://render.com)
2. **New → Web Service → Connect GitHub repository**
3. Select this repository
4. Render detects `render.yaml` automatically – just click **Deploy**
5. After deploy, copy your service URL:
   `https://python-openhab-rest-client-test-app.onrender.com`

### 3. Enable GitHub Pages

In your GitHub repository:
**Settings → Pages → Source: GitHub Actions**

The workflow in `.github/workflows/deploy.yml` deploys `index.html` automatically on every push to `main`.

Your frontend will be live at:
```
https://michdo93.github.io/python-openhab-rest-client-test-app/
```

### 4. Set up myopenhab.org

1. Install the **openHAB Cloud Connector** add-on in openHAB
2. Register at [myopenhab.org](https://myopenhab.org)
3. Connect your instance

### 5. Use the App

Open the GitHub Pages URL, then:

- **Backend URL** – paste your Render.com service URL
- **openHAB URL** – `https://home.myopenhab.org`
- **Username / Password** – your myopenhab.org credentials
  *(or use an API Token instead)*
- Click **Verbinden**

---

## Backend API

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/`            | Health check |
| POST | `/api/connect` | Connect to openHAB |
| GET  | `/api/classes` | List all classes and methods |
| POST | `/api/call`    | Call any REST API method |
| POST | `/api/test`    | Run a test method |
| GET  | `/api/sse`     | Proxy SSE event stream |

### Example – `/api/call`

```json
POST /api/call
{
  "class": "Items",
  "method": "getAllItems",
  "args": [],
  "kwargs": {}
}
```

### Example – `/api/sse`

```
GET /api/sse?type=ItemEvents&method=ItemStateChangedEvent&args=[]
```

---

## Local Development

```bash
pip install -r requirements.txt
python app.py
# Backend runs on http://localhost:5000
# Set Backend URL in the frontend to http://localhost:5000
```

---

## Related Projects

| Library | Language | Test App |
|---------|----------|----------|
| [js-openhab-rest-client](https://github.com/Michdo93/js-openhab-rest-client) | JavaScript | [Demo](https://michdo93.github.io/js-openhab-rest-client/) |
| [nodejs-openhab-rest-client](https://github.com/Michdo93/nodejs-openhab-rest-client) | Node.js | [Demo](https://michdo93.github.io/nodejs-openhab-rest-client-test-app/) |
| [python-openhab-rest-client](https://github.com/Michdo93/python-openhab-rest-client) | Python | [Demo](https://michdo93.github.io/python-openhab-rest-client-test-app/) |

---

## License

MIT
