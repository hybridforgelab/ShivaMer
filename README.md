#  ShivaMer — Python → Mermaid Converter

**ShivaMer** is a web app that converts **Python code** into **Mermaid diagrams** in real time.  
It helps you visualize logic flow from functions, conditions, and loops as flowcharts you can export to **PNG** or **.mmd**.

---

##  Features

- Convert Python code into **Mermaid flowcharts**
- Real-time preview (auto or manual)
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

Backend (FastAPI):
```bash
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

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

---

##  Contributing

Contributions are welcome!  
To contribute:

1. Fork the repository  
2. Create a feature branch:  
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit and push changes  
4. Open a Pull Request  

---

## License

This project is open-source under the **MIT License**.  
Feel free to use, modify, and share it just give credit to the original authors.

---

## Credits

Developed and maintained by [**HybridForgeLab**](https://hybridforgelab.com).  
> *"Code. Visualize. Understand."*
