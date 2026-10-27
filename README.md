#  ShivaMer — Python → Mermaid Converter

**ShivaMer** is a web app that converts **Python code** into **Mermaid diagrams** in real time.  
It helps you visualize logic flow from functions, conditions, and loops as flowcharts you can export to **PNG** or **.mmd**.

---

##  Features

- Convert Python code into **Mermaid flowcharts**
- Real-time preview (auto, debounced, or manual) with inline syntax errors
- Export diagrams as **PNG** or **.mmd**
- Powered by **FastAPI (backend)** + **React + Vite + TailwindCSS (frontend)**
- Supports **Docker Compose** for local testing

---

## Quick Start

### Local development
```bash
# Clone repo
git clone https://github.com/hybridforgelab/shivamer.git
cd shivamer/frontend

# Install dependencies
npm install

# Run frontend (default API is http://localhost:8000)
npm run dev
```

Backend (FastAPI, Python 3.12):
```bash
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Tests and lint:
```bash
cd backend
pip install -r requirements-dev.txt
pytest -q && ruff check .
```

The API only accepts browser requests from the origins in `ALLOWED_ORIGINS`
(comma separated; defaults to the production site plus `localhost:5173`/`8080`).

Then open: [http://localhost:5173](http://localhost:5173)

---

### Docker Compose (optional)
```bash
docker compose up --build
```
Frontend → `http://localhost:8080`  
Backend → `http://localhost:8000`

---

## How It Works

1. The **frontend** sends your Python code to the backend via `/convert` (POST).  
2. The **FastAPI backend** parses it with Python’s `ast` module.  
3. The backend returns a **Mermaid flowchart definition** (`flowchart TD ...`).  
4. The **frontend** renders it using the **Mermaid.js** library.

### What gets drawn

| Python | Diagram |
|---|---|
| `def` / `async def` | a subgraph with its own start and End |
| `class` | a subgraph containing its methods |
| `if` / `elif` / `else` | decision with Yes / No branches that join again |
| `for`, `while` (+ `else`) | decision with a loop-back edge; `break` / `continue` follow the real flow |
| `try` / `except` / `finally`, `with`, `match` | their blocks in order; `except` is reached through an `error` edge |
| `return`, `raise` | go straight to the End of the function |
| `input(...)`, `print(...)` | I/O parallelograms |
| anything else | a box with the statement's code |

### Deployment

- **Frontend:** `.github/workflows/deploy.yml` builds on every PR and publishes to GitHub Pages
  (`shivamer.hybridforgelab.com`) on push to `main`.
- **Backend:** `.github/workflows/backend.yml` runs ruff + pytest, then on `main` deploys
  `backend/` to the Fly app `shivamer-backend` (`api-shivamer.hybridforgelab.com`) and runs a
  smoke test. The deploy step needs the `FLY_API_TOKEN` repository secret; without it the job
  skips with a warning and you can deploy by hand with `cd backend && flyctl deploy`.

---

## Contributing

Contributions are welcome! See the [contributing guide](https://github.com/hybridforgelab/.github/blob/main/CONTRIBUTING.md): open an issue first for anything bigger than a small fix, use [Conventional Commits](https://www.conventionalcommits.org/) for the pull request title, and run the backend checks (`pytest -q && ruff check .`, see *Tests and lint* above) before opening the pull request. Everyone follows the [code of conduct](https://github.com/hybridforgelab/.github/blob/main/CODE_OF_CONDUCT.md).

---

## License

This project is open-source under the **MIT License**.  
Feel free to use, modify, and share it just give credit to the original authors.

---

## Credits

Developed and maintained by [**HybridForgeLab**](https://hybridforgelab.com).  
> *"Code. Visualize. Understand."*
