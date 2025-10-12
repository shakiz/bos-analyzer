
import React, { useState } from "react";
import { Upload, ShoppingBag, BarChart3 } from "lucide-react";
import SizeAnalyticsChart from "./SizeAnalyticsChart";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [files, setFiles] = useState([]);

  const handleFileUpload = async (e) => {
    const selected = Array.from(e.target.files);
    if (selected.length === 0) return;
    setFiles(selected);
    setLoading(true);
    setError(null);
    setResults(null);
    const formData = new FormData();
    selected.forEach((f) => formData.append("files", f));
    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Failed to analyze files");
      const data = await res.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 to-purple-50 flex flex-col items-center justify-center py-10 px-2">
      <div className="max-w-6xl w-full mx-auto text-center mb-8">
        <h1 className="text-5xl font-bold text-gray-800 mb-3">Box of Secrets</h1>
        <p className="text-xl text-gray-600">Shoe Size Analysis & Demand Prediction Tool</p>
      </div>

  <div className="max-w-6xl w-full mx-auto bg-white rounded-2xl shadow-xl p-8 mb-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 text-left">Upload Your Shipment Documents</h2>
  <label className="flex flex-col items-center justify-center w-full h-40 border-4 border-dashed border-pink-300 rounded-xl cursor-pointer bg-pink-50 hover:bg-pink-100 transition-all">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <Upload className="w-16 h-16 text-pink-600 mb-4" />
            <p className="mb-2 text-xl font-semibold text-gray-700">
              Click to upload or drag and drop
            </p>
            <p className="text-sm text-gray-500">
              DOCX, DOC, or TXT files (Multiple files supported)
            </p>
          </div>
          <input
            type="file"
            className="hidden"
            accept=".doc,.docx,.txt"
            multiple
            onChange={handleFileUpload}
            disabled={loading}
          />
        </label>
        {loading && (
          <div className="mt-6 text-center text-lg text-pink-600 font-semibold">Analyzing files...</div>
        )}
        {error && (
          <div className="mt-6 text-center text-red-600 font-semibold">{error}</div>
        )}
        {results && (
          <>
            <div className="flex flex-col md:flex-row gap-8 mt-8">
              {/* Overall Bar Chart */}
              <div className="flex-1">
                <SizeAnalyticsChart topSizes={results.top_sizes} />
              </div>
            </div>

            {/* Top Customers Table */}
            {results.top_customers && results.top_customers.length > 0 && (
              <div className="mt-10">
                <h4 className="text-xl font-bold text-blue-700 mb-4 flex items-center gap-2">
                  <span role="img" aria-label="customer">👥</span> Top 20 Customers
                </h4>
                <div className="overflow-x-auto">
                  <table className="min-w-[400px] w-full bg-white border border-blue-100 rounded-lg">
                    <thead>
                      <tr className="bg-blue-100 text-blue-700">
                        <th className="px-4 py-2 text-left">Customer Number</th>
                        <th className="px-4 py-2 text-left">Order Count</th>
                        <th className="px-4 py-2 text-left">Files</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.top_customers.map((c, i) => (
                        <tr key={c.customer} className="border-t border-gray-100">
                          <td className="px-4 py-2 font-mono">{c.customer}</td>
                          <td className="px-4 py-2">{c.order_count}</td>
                          <td className="px-4 py-2 text-xs text-gray-500">{c.filename || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Per-file breakdown: each file gets its own table */}
            <div className="mt-8">
              <h4 className="text-lg font-bold text-gray-700 mb-3">Detailed Size Breakdown by File</h4>
              <div className="flex flex-col gap-8">
                {results.per_file.map((file, idx) => (
                  <div key={file.filename} className="bg-white rounded-xl border border-gray-200 shadow p-4">
                    <div className="font-semibold text-pink-700 mb-2">{file.filename}</div>
                    <div className="overflow-x-auto">
                      <table className="min-w-[300px] w-full bg-white border border-gray-100 rounded-lg">
                        <thead>
                          <tr className="bg-pink-100 text-pink-700">
                            <th className="px-4 py-2 text-left">Shoe Size</th>
                            <th className="px-4 py-2 text-left">Orders</th>
                          </tr>
                        </thead>
                        <tbody>
                          {file.top_sizes.length === 0 ? (
                            <tr><td colSpan={2} className="px-4 py-2 text-gray-400 italic">No sizes found</td></tr>
                          ) : (
                            file.top_sizes.map((s, j) => (
                              <tr key={file.filename + '-' + s.size} className="border-t border-gray-100">
                                <td className="px-4 py-2">{s.size}</td>
                                <td className="px-4 py-2">{s.count}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

  <div className="max-w-6xl w-full mx-auto bg-white rounded-2xl shadow-xl p-8">
        <h3 className="text-xl font-bold text-gray-800 mb-4 text-left">How to Use</h3>
        <ol className="space-y-3 text-gray-700 list-decimal list-inside">
          <li>Export your shipment documents from Google Docs as .docx or .txt files</li>
          <li>Upload one or more files using the upload area above</li>
          <li>The system will automatically detect product names and analyze size distribution</li>
          <li>View comprehensive analytics, trends, and stocking recommendations</li>
        </ol>
      </div>
    </div>
  );
}
