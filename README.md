# mcp-wikijs

A Python-based Model Context Protocol (MCP) server designed to bridge [Wiki.js](https://js.wiki/) and 
Google Drive content into your LLM client (e.g., Claude Desktop).

Unlike standard API wrappers, `mcp-wikijs` acts as an ingestion and retrieval pipeline. 
It scrapes content from your knowledge bases, processes it into vector representations, 
and exposes context directly to AI models.

## 🏗️ Architecture & Component Overview

The repository is structured to handle ingestion, vector management, and protocol communication:

* **`mcp-wikijs.py`**: The core MCP server entry point handling tool registration and LLM client communications.
* **`wikiscreaper.py` & `wikijsclient.py**`: Automated scraper and client to pull down structured knowledge base articles from Wiki.js.
* **`drivescreaper.py` & `gdrive.py**`: Google Drive scraper and integration modules to pull files/docs from designated folders.
* **`teivector.py`**: Handles embedding generation and vector operations (likely targeting a Text Embeddings Inference microservice).
* **`configmanager.py` & `middlewares/tokenauth.py**`: Manages configuration parsing and secure token-based authentication.

---

## 🛠️ Features

* **Dual-Source Ingestion**: Pulls information from both Wiki.js and Google Drive.
* **Incremental Syncing**: Tracked via state files (`*.lastrun`) to only scrape updated items.
* **Vector Search Capabilities**: Prepared to provide dense semantic retrieval to LLMs instead of simple keyword matching.
* **Automated Scheduling**: Ready-to-use shell scripts to run background scraping tasks.

---

## 📋 Prerequisites

* **Python 3.10+**
* A running **Wiki.js** instance with an API token.
* A **Google Cloud Project** with service account keys (for Google Drive access).
* An embedding service endpoint (if utilizing `teivector`).

---

## 🚀 Installation & Setup

1. **Clone the repository:**
```bash

```



git clone https://github.com/grtxx/mcp-wikijs.git
cd mcp-wikijs

```

2. **Set up a virtual environment & install dependencies:**
   ```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

3. **Configure Environment Variables:**
Copy the sample configuration file to customize your setup:
```bash

```



cp mcp-config.sample.json mcp-config.json

```
   *Make sure to populate your specific Wiki.js endpoints, API keys, and Google Drive credentials inside your configurations.*

---

## ⚙️ Usage & Operation

### Running the MCP Server
To spin up the main protocol server over standard I/O streams:
```bash
python mcp-wikijs.py

```

### Running the Ingestion Scrapers

You can manually trigger knowledge collection or hook these up to a system crontab using the provided utility scripts:

* **Wiki.js Scraper:**
```bash

```



./mcp-wikiscreaper.sh

```
*   **Google Drive Scraper:**
    ```bash
./mcp-drivescreaper.sh

```

Logs for background sync runs can be actively monitored in the `log/` folder (`run.log`, `wiki-screaper.log`, `drive-screaper.log`).

---

## 🔌 Integration with Claude Desktop

To register this server with your Claude desktop application, add the following configuration block to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-wikijs": {
      "command": "/absolute/path/to/mcp-wikijs/venv/bin/python",
      "args": ["/absolute/path/to/mcp-wikijs/mcp-wikijs.py"]
    }
  }
}

```

---

## 📄 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).