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

export default function SizeAnalyticsChart({ topSizes }) {
  if (!topSizes || topSizes.length === 0) return null;

  // Overall bar chart data
  const overallData = {
    labels: topSizes.map((s) => `Size ${s.size}`),
    datasets: [
      {
        label: "Total Orders",
        data: topSizes.map((s) => s.count),
        backgroundColor: "#f472b6",
      },
    ],
  };

  // Golden sizes (top 5) bar chart data
  const goldenSizes = topSizes.slice(0, 5);
  const goldenData = {
    labels: goldenSizes.map((s) => `Size ${s.size}`),
    datasets: [
      {
        label: "Golden Sizes Orders",
        data: goldenSizes.map((s) => s.count),
        backgroundColor: "#fde68a",
        borderColor: "#f59e42",
        borderWidth: 2,
      },
    ],
  };

  return (
    <div className="flex flex-col md:flex-row gap-8 mt-8">
      <div className="flex-1 bg-white rounded-xl shadow p-4">
        <h4 className="font-bold text-pink-700 mb-2 text-2xl">Overall Size Distribution</h4>
        <Bar data={overallData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
      </div>
      <div className="flex-1 bg-white rounded-xl shadow p-4">
        <h4 className="font-bold text-yellow-600 mb-2 text-2xl flex items-center gap-2">
          <span role="img" aria-label="star">⭐</span> Golden Sizes Recommendation
        </h4>
        <Bar data={goldenData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
        <div className="text-sm text-gray-500 mt-4 text-center">These sizes are most frequently ordered and recommended for future stock.</div>
      </div>
    </div>
  );
}
