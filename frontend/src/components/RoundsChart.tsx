import {
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
  Filler
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { MultiplierPoint } from "../types";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export function RoundsChart({ points }: { points: MultiplierPoint[] }) {
  // Only show last 60 points for performance and clarity
  const displayPoints = points.slice(-60);
  const labels = displayPoints.map((point) => new Date(point.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
  const raw = displayPoints.map((point) => point.value);
  const smooth = displayPoints.map((point) => point.smoothed);

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0 relative">
        <Line
          data={{
            labels,
            datasets: [
              {
                label: "Trajectory",
                data: smooth,
                borderColor: "#a855f7",
                backgroundColor: (context) => {
                  const chart = context.chart;
                  const {ctx, chartArea} = chart;
                  if (!chartArea) return undefined;
                  const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                  gradient.addColorStop(0, 'rgba(168, 85, 247, 0.2)');
                  gradient.addColorStop(1, 'rgba(168, 85, 247, 0)');
                  return gradient;
                },
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                borderWidth: 3,
              },
              {
                label: "Raw Feed",
                data: raw,
                borderColor: "rgba(255, 255, 255, 0.1)",
                borderDash: [5, 5],
                tension: 0.2,
                pointRadius: 2,
                pointBackgroundColor: (context) => {
                   const point = displayPoints[context.dataIndex];
                   if (point?.state === 'crashed') return '#ef4444';
                   if (point?.state === 'waiting') return '#22c55e';
                   return 'rgba(255, 255, 255, 0.3)';
                },
                borderWidth: 1,
              }
            ]
          }}
          options={{
            animation: {
              duration: 400
            },
            maintainAspectRatio: false,
            responsive: true,
            plugins: { 
              legend: { display: false },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleFont: { size: 10 },
                bodyFont: { size: 12 },
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 10,
                displayColors: false,
                callbacks: {
                  label: (context) => `Multiplier: ${context.parsed.y ? context.parsed.y.toFixed(2) : '0.00'}x`
                }
              }
            },
            scales: {
              x: { 
                grid: { display: false },
                ticks: { color: "rgba(255,255,255,0.2)", maxTicksLimit: 8, font: { size: 9 } } 
              },
              y: { 
                position: 'right',
                grid: { color: "rgba(255,255,255,0.03)" },
                ticks: { color: "rgba(255,255,255,0.3)", font: { size: 10 } } 
              }
            }
          }}
        />
      </div>
    </div>
  );
}
