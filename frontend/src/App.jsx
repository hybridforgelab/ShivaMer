import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import Editor from "react-monaco-editor";
import * as htmlToImage from "html-to-image";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

const EXAMPLE = `def fizzbuzz(n):
    for i in range(1, n+1):
        if i % 15 == 0:
            print("FizzBuzz")
        elif i % 3 == 0:
            print("Fizz")
        elif i % 5 == 0:
            print("Buzz")
        else:
            print(i)
`;

function MobileNotice() {
  const [hidden, setHidden] = useState(false);

  // Read localStorage only on the client after mount
  useEffect(() => {
    try {
      if (localStorage.getItem("hideMobileNotice") === "1") {
        setHidden(true);
      }
    } catch {/* ignore */}
  }, []);

  if (hidden) return null;

  return (
    <div className="md:hidden fixed bottom-0 inset-x-0 z-50" role="status" aria-live="polite">
      <div className="m-3 rounded-lg bg-amber-100 text-amber-900 p-3 shadow-lg flex items-start gap-3">
        <p className="text-sm">
          We’re updating our site for a better mobile experience. For now, it’s best viewed on desktop.
        </p>
        <button
          onClick={() => { localStorage.setItem("hideMobileNotice", "1"); setHidden(true); }}
          aria-label="Dismiss notice"
          className="ml-auto px-2 py-1 text-xs rounded bg-amber-200 hover:bg-amber-300"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}


export default function App() {
  const [code, setCode] = useState(EXAMPLE);
  const [diagram, setDiagram] = useState("flowchart TD\n");
  const [auto, setAuto] = useState(true);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  async function convert() {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/convert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      if (!resp.ok) {
        const { detail } = await resp.json();
        alert(detail || "Conversion failed.");
        return;
      }
      const data = await resp.json();
      setDiagram(data.mermaid);
    } catch (e) {
      alert("Failed to connect to the API at " + API_BASE);
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (auto) convert();
  }, [code]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.innerHTML = "";
    const id = "m" + Math.random().toString(36).slice(2);
    mermaid
      .render(id, diagram)
      .then(({ svg }) => {
        el.innerHTML = svg;
      })
      .catch(console.error);
  }, [diagram]);

  async function exportPNG() {
    const el = containerRef.current;
    if (!el) return;
    const dataUrl = await htmlToImage.toPng(el);
    const a = document.createElement("a");
    a.download = "diagram.png";
    a.href = dataUrl;
    a.click();
  }

  function exportMMD() {
    const blob = new Blob([diagram], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "diagram.mmd";
    a.click();
    URL.revokeObjectURL(url);
  }

  function loadSample(name) {
    if (name === "FizzBuzz") setCode(EXAMPLE);
    if (name === "If/Else")
      setCode(`age = int(input('Please enter your age: '))
if age >= 18:
    print('Authorized')
else:
    print('Not Authorized')`);
    if (name === "While")
      setCode(`def countdown(n):
    while n > 0:
        print(n)
        n -= 1
    return "go!"`);
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-white">
            ShivaMer — Python → Mermaid
          </h1>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-sm">
              <input
                type="checkbox"
                checked={auto}
                onChange={(e) => setAuto(e.target.checked)}
              />
              Auto
            </label>
            <button
              onClick={convert}
              className="px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50 hover:bg-blue-700"
              disabled={loading}
            >
              {loading ? "Converting..." : "Convert"}
            </button>
            <button
              onClick={exportPNG}
              className="px-3 py-1 rounded border border-gray-500 hover:bg-gray-800"
            >
              Export PNG
            </button>
            <button
              onClick={exportMMD}
              className="px-3 py-1 rounded border border-gray-500 hover:bg-gray-800"
            >
              Export .mmd
            </button>
          </div>
        </div>
        <div className="flex gap-2 text-sm">
          <button
            onClick={() => loadSample("FizzBuzz")}
            className="px-2 py-1 rounded border border-gray-500 hover:bg-gray-800"
          >
            Example: FizzBuzz
          </button>
          <button
            onClick={() => loadSample("If/Else")}
            className="px-2 py-1 rounded border border-gray-500 hover:bg-gray-800"
          >
            Example: If/Else
          </button>
          <button
            onClick={() => loadSample("While")}
            className="px-2 py-1 rounded border border-gray-500 hover:bg-gray-800"
          >
            Example: While
          </button>
        </div>
        <Editor
          height="70vh"
          language="python"
          theme="vs-dark"
          value={code}
          onChange={setCode}
          options={{ minimap: { enabled: false }, fontSize: 14, lineNumbers: "on" }}
        />
      </div>

      <div className="bg-gray-800 rounded shadow p-3 overflow-auto">
        <div ref={containerRef} className="mermaid" />
      </div>

      <footer className="col-span-2 text-center text-gray-500 text-sm mt-6 border-t border-gray-700 pt-3">
        <div className="flex flex-col items-center gap-2">
          <p>
            Powered by{" "}
            <a
              href="https://hybridforgelab.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-300"
            >
              hybridforgelab.com
            </a>
          </p>
          <a
            href="https://github.com/hybridforgelab/shivamer"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-white"
            aria-label="GitHub Repository"
            title="GitHub Repository"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="w-5 h-5"
            >
              <path
                fillRule="evenodd"
                d="M12 2C6.477 2 2 6.484 2 12.017c0 4.426 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483
                   0-.237-.009-.868-.014-1.703-2.782.604-3.369-1.343-3.369-1.343-.454-1.153-1.11-1.46-1.11-1.46-.908-.62.069-.608.069-.608
                   1.004.07 1.532 1.032 1.532 1.032.892 1.53 2.341 1.088 2.91.833.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951
                   0-1.093.39-1.988 1.029-2.688-.103-.254-.447-1.272.098-2.65 0 0 .84-.269 2.75 1.026A9.564 9.564 0 0 1 12 6.844
                   c.85.004 1.705.115 2.504.337 1.909-1.295 2.748-1.026 2.748-1.026.547 1.378.203 2.396.1 2.65.64.7
                   1.028 1.595 1.028 2.688 0 3.848-2.338 4.695-4.566 4.944.36.31.682.922.682 1.857
                   0 1.34-.012 2.422-.012 2.75 0 .268.18.58.688.481A10.02 10.02 0 0 0 22 12.017C22 6.484 17.523 2 12 2z"
                clipRule="evenodd"
              />
            </svg>
          </a>
        </div>
      </footer>

      <MobileNotice />
    </div>
  );
}
