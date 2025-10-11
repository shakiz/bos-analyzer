import React, { useState } from "react";
import { Upload, FileText, X, BarChart3 } from "lucide-react";


export default function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    const selected = Array.from(e.target.files);
    const valid = selected.filter((f) => f.name.endsWith(".docx"));
    setFiles((prev) => [...prev, ...valid]);
  };

  const removeFile = (i) => {
    setFiles((prev) => prev.filter((_, idx) => idx !== i));
  };

  const analyze = async () => {
    if (files.length === 0) return alert("Please upload at least one DOCX file");
    setLoading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResults(data);
    } catch (err) {
      alert("Error analyzing files: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-10 flex flex-col items-center">
      <div className="bg-white w-full max-w-xl rounded-2xl shadow p-6">
        <h1 className="text-2xl font-bold mb-4 text-center">
          🩰 Box of Secrets - Order Analyzer
        </h1>

        <label className="flex flex-col items-center justify-center w-full p-6 border-2 border-dashed rounded-lg cursor-pointer hover:bg-gray-50">
          <Upload className="h-6 w-6 mb-2 text-gray-500" />
          <p className="text-sm text-gray-600">Click or drag .docx files to upload</p>
          <input
            type="file"
            accept=".docx"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
        </label>

        {files.length > 0 && (
          <ul className="mt-4 space-y-2">
            {files.map((f, i) => (
              <li key={i} className="flex items-center justify-between bg-gray-100 px-3 py-2 rounded-md">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-gray-600" />
                  <span className="text-sm text-gray-700">{f.name}</span>
                </div>
                <button onClick={() => removeFile(i)} className="text-gray-500 hover:text-red-500">
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <button
          onClick={analyze}
          disabled={loading}
          className="mt-5 w-full bg-pink-600 hover:bg-pink-700 text-white py-2 rounded-lg font-medium disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze Orders"}
        </button>

        {results && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" /> Top 5 Shoe Sizes
            </h3>
            <ul className="space-y-1">
              {results.top_sizes.length === 0 ? (
                <li>No sizes found in the documents</li>
              ) : (
                results.top_sizes.map((s, i) => (
                  <li
                    key={i}
                    className="flex justify-between p-2 bg-gray-100 rounded"
                  >
                    <span>Size {s.size}</span>
                    <span className="font-medium">{s.count} orders</span>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
