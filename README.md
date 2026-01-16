# OSRS Wiki RAG System

A local Retrieval-Augmented Generation (RAG) system for querying the Old School RuneScape (OSRS) wiki. This system scrapes wiki content, creates embeddings, stores them in a vector database, and uses a local LLM (Ollama with Qwen 2.5 14B) to answer questions about OSRS.

## Features

- 🔍 **Wiki Scraping**: Automated scraping of OSRS wiki pages with structured data extraction
- 🧠 **Intelligent Chunking**: Preserves related information together (item stats, quest requirements, etc.)
- 📊 **Vector Database**: Uses Chroma for fast similarity search
- 🤖 **Local LLM**: Uses Ollama with Qwen 2.5 14B for generation (optimized for RTX 4080)
- 💬 **Dual Interfaces**: Both CLI and Streamlit web UI
- ⚡ **Fast Retrieval**: Optimized for speed with top-k retrieval
- 🛡️ **Security Features**:
  - Input validation and sanitization
  - Rate limiting (max 1 query per 2 seconds)
  - Prompt injection prevention
  - Query/response logging (with clear functionality)
  - Max token limits for responses (1000 tokens)
  - Basic authentication for network-exposed UI

## Requirements

- Python 3.8+
- Ollama installed and running with Qwen 2.5 14B model
- RTX 4080 (or compatible GPU) for optimal performance
- ~10GB free disk space for data and vector database

## Installation

1. **Clone or download this repository**
   ```bash
   cd osrssage
   ```

2. **Create and activate a virtual environment** (recommended):
   
   **On Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
   
   **On macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   You should see `(venv)` in your terminal prompt when activated.
   
   **Quick setup scripts:**
   - Windows: Run `setup_venv.bat`
   - macOS/Linux: Run `bash setup_venv.sh` or `chmod +x setup_venv.sh && ./setup_venv.sh`

3. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Install and setup Ollama:**
   - Download from [https://ollama.ai](https://ollama.ai)
   - Pull the Qwen 2.5 14B model:
     ```bash
     ollama pull qwen2.5:14b
     ```
   - Ensure Ollama is running (default: http://localhost:11434)

5. **Verify installation:**
   ```bash
   python quick_start.py
   ```
   This will check all dependencies and setup.

6. **Configure the system:**
   - Edit `config.yaml` to adjust settings (chunk size, retrieval parameters, etc.)

## Usage

### Step 1: Scrape Wiki Data

Scrape content from the OSRS wiki:

```bash
python scrape_wiki.py
```

This will:
- Download pages from configured categories (Items, Quests, Skills, etc.)
- Extract structured data (infoboxes, tables, lists)
- Save raw data to `data/raw/`

**Note:** Initial scraping may take 30-60 minutes depending on the number of pages. You can limit pages in `config.yaml` by setting `max_pages`.

### Step 2: Process Data

Process scraped data into intelligent chunks:

```bash
python process_data.py
```

This will:
- Load scraped wiki pages
- Create intelligent chunks preserving related information
- Save processed chunks to `data/processed/`

### Step 3: Create Vector Database

Generate embeddings and build the vector database:

```bash
python create_vector_db.py
```

To rebuild from scratch:
```bash
python create_vector_db.py --clear
```

This will:
- Load processed chunks
- Generate embeddings using sentence-transformers
- Store in Chroma vector database at `data/vector_db/`

**Note:** First run will download the embedding model (~1.3GB for bge-large-en-v1.5).

### Step 4: Query the System

#### CLI Interface

**Make sure your virtual environment is activated first!**

Run the terminal interface:

```bash
python cli_interface.py
```

Type questions and get answers. Commands:
- Type `quit` or `exit` to exit
- Type `clear` to clear the screen
- Type `logs` to view query log count
- Type `clearlogs` to clear query logs

#### Streamlit UI

**Make sure your virtual environment is activated first!**

Run the web interface:

```bash
streamlit run streamlit_ui.py
```

Open your browser to the displayed URL (usually http://localhost:8501).

**Note:** Remember to activate your virtual environment (`venv\Scripts\activate` on Windows, `source venv/bin/activate` on macOS/Linux) before running any scripts.

## Configuration

Edit `config.yaml` to customize:

- **Wiki scraping**: Categories, max pages, output directory
- **Text processing**: Chunk size, overlap, preservation settings
- **Vector DB**: Embedding model, batch size, collection name
- **RAG**: Top-k retrieval, similarity threshold, context length
- **LLM**: Model name, temperature, max tokens, system prompt
- **Security**: Rate limiting, input validation, logging settings
- **Authentication**: Enable/disable auth, username/password (for network-exposed UI)

### Security Settings

The system includes comprehensive security features:

- **Input Validation**: Validates and sanitizes all user queries, detects prompt injection attempts
- **Rate Limiting**: Default 2 seconds between queries (configurable)
- **Prompt Injection Prevention**: Enhanced system prompt and pattern detection
- **Query Logging**: All queries and responses logged to `logs/query_log.jsonl` (can be cleared)
- **Token Limits**: Hard limit of 1000 tokens for responses (configurable)
- **Authentication**: Basic auth for Streamlit UI when exposed to network (disabled by default)

To enable authentication for network access:
1. Set `auth.enabled: true` in `config.yaml`
2. Change `auth.username` and `auth.password` (or use environment variables in production)

### Embedding Models

Two recommended models:
- `BAAI/bge-large-en-v1.5` (default): Better quality, larger (~1.3GB)
- `sentence-transformers/all-MiniLM-L6-v2`: Faster, smaller (~80MB)

Change in `config.yaml` under `vector_db.embedding_model`.

## Project Structure

```
osrssage/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── scrape_wiki.py           # Wiki scraping script
├── process_data.py          # Data processing and chunking
├── create_vector_db.py      # Vector database creation
├── rag_system.py            # Core RAG system
├── cli_interface.py         # Terminal interface
├── streamlit_ui.py          # Web UI
├── README.md                # This file
├── data/
│   ├── raw/                 # Scraped wiki pages (JSON)
│   ├── processed/           # Processed chunks (JSON)
│   └── vector_db/           # Chroma vector database
└── logs/                    # Log files
```

## Updating Wiki Data

To update the wiki data:

1. Run `scrape_wiki.py` again (it will skip already scraped pages)
2. Run `process_data.py` to reprocess
3. Run `create_vector_db.py --clear` to rebuild the vector database

Or modify `scrape_wiki.py` to only fetch new/updated pages.

## Security Notes

### For Production Use

If exposing the Streamlit UI to a network:

1. **Enable Authentication**: Set `auth.enabled: true` in `config.yaml` and use strong credentials
2. **Use Environment Variables**: Store credentials in environment variables instead of config file
3. **HTTPS**: Use a reverse proxy (nginx, Traefik) with HTTPS
4. **Firewall**: Restrict access to trusted IPs if possible
5. **Log Monitoring**: Regularly review query logs for suspicious activity
6. **Rate Limiting**: Adjust `security.rate_limit_interval` based on your needs

### Query Logs

Query logs are stored in `logs/query_log.jsonl` in JSONL format. Each entry includes:
- Timestamp
- Query hash (for privacy)
- Query preview
- Response metadata
- Sources referenced

To clear logs:
- **CLI**: Type `clearlogs` command
- **Streamlit UI**: Click "Clear Query Logs" in sidebar
- **Manual**: Delete `logs/query_log.jsonl`

## Troubleshooting

### Ollama Connection Error

- Ensure Ollama is running: `ollama list`
- Check the base URL in `config.yaml` matches your Ollama instance
- Verify the model is installed: `ollama show qwen2.5:14b`

### Vector Database Not Found

- Run `create_vector_db.py` first
- Check that `data/processed/processed_chunks.json` exists

### Out of Memory

- Reduce `batch_size` in `config.yaml`
- Use smaller embedding model (`all-MiniLM-L6-v2`)
- Reduce `max_pages` when scraping

### Slow Performance

- Ensure GPU is being used by Ollama (check Ollama logs)
- Use smaller embedding model for faster retrieval
- Reduce `top_k` in RAG settings
- Reduce `max_context_length` to limit context size

## Performance Tips

For RTX 4080 optimization:

1. **Ollama GPU**: Ensure Ollama is using GPU (check with `ollama ps`)
2. **Batch Processing**: Increase `batch_size` in config for faster embedding creation
3. **Model Selection**: Qwen 2.5 14B runs well on RTX 4080 with 16GB VRAM
4. **Context Length**: Keep `max_context_length` reasonable (4000 chars default)

## License

This project is for educational purposes. Respect the OSRS wiki's terms of service and robots.txt when scraping.

## Acknowledgments

- Old School RuneScape Wiki: https://oldschool.runescape.wiki/
- Chroma: https://www.trychroma.com/
- Ollama: https://ollama.ai/
- Sentence Transformers: https://www.sbert.net/
