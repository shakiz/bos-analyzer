import React from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function SizeAnalyticsChart({ topSizes = [], predictedSizes = [] }) {
  if (!topSizes || topSizes.length === 0) return null;

  // --- Overall (historical) bar chart ---
  const overallData = {
    labels: topSizes.map((s) => `Size ${s.size}`),
    datasets: [
      {
        label: "Total Orders",
        data: topSizes.map((s) => s.count),
        backgroundColor: "rgba(244, 114, 182, 0.8)", // pink
        borderColor: "#ec4899",
        borderWidth: 1,
      },
    ],
  };

  // --- Predicted sizes chart ---
  const hasPredictions = predictedSizes && predictedSizes.length > 0;
  const predictedData = hasPredictions
    ? {
        labels: predictedSizes.map((s) => `Size ${s.size}`),
        datasets: [
          {
            label: "Predicted Future Demand",
            data: predictedSizes.map(
              (s) => s.predicted_demand || s.count || 0
            ),
            backgroundColor: "rgba(253, 224, 71, 0.8)", // yellow
            borderColor: "#f59e0b",
            borderWidth: 2,
          },
        ],
      }
    : null;

  const baseOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `${context.raw} orders`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { precision: 0 },
      },
    },
  };

  return (
    <div className="flex flex-col md:flex-row gap-8 mt-8">
      {/* Historical sizes chart */}
      <div className="flex-1 bg-white rounded-xl shadow p-4">
        <h4 className="font-bold text-pink-700 mb-2 text-2xl">
          Overall Size Distribution
        </h4>
        <Bar data={overallData} options={baseOptions} />
        <div className="text-sm text-gray-500 mt-3 text-center">
          Shows the most frequently ordered shoe sizes based on uploaded documents.
        </div>
      </div>

      {/* Predicted (future) chart */}
      {hasPredictions && (
        <div className="flex-1 bg-white rounded-xl shadow p-4">
          <h4 className="font-bold text-yellow-600 mb-2 text-2xl flex items-center gap-2">
            <span role="img" aria-label="crystal-ball">🔮</span> Predicted Next Cycle Demand
          </h4>
          <Bar data={predictedData} options={baseOptions} />
          <div className="text-sm text-gray-500 mt-3 text-center">
            These sizes are predicted to have the highest demand next cycle — great candidates for stocking.
          </div>
        </div>
      )}
    </div>
  );
}
