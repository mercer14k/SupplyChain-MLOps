import { useEffect, useRef, type ReactNode } from "react";
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  X,
  Inbox,
  LoaderCircle,
} from "lucide-react";
import type { Point } from "./types";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Inbox size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={20} /> Loading operational evidence…
    </div>
  );
}
export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-heading">
        <div>
          {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "modal wide" : "modal"}
      onCancel={onClose}
    >
      <div className="modal-head">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Pagination({
  total,
  offset,
  onChange,
}: {
  total: number;
  offset: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total
          ? `${offset + 1}–${Math.min(offset + 25, total)} of ${total}`
          : "0 results"}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - 25))}
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={offset + 25 >= total}
          onClick={() => onChange(offset + 25)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}
export function TextLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-link" onClick={onClick}>
      {children}
      <ArrowUpRight size={15} />
    </button>
  );
}
export function JsonEvidence({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
export function Chart({
  points,
  anomaly = false,
}: {
  points: Point[];
  anomaly?: boolean;
}) {
  if (!points.length)
    return (
      <Empty title="No chart evidence">
        Train a model to see chronological holdout results.
      </Empty>
    );
  const values = points.flatMap((p) =>
    anomaly ? [p.score ?? 0] : [p.actual ?? 0, p.prediction ?? 0],
  );
  const min = 0,
    max = Math.max(1, ...values) * 1.2,
    w = 840,
    h = 236,
    pad = 42;
  const px = (i: number) =>
    pad + (i * (w - pad - 20)) / Math.max(1, points.length - 1);
  const py = (n: number) => h - 30 - ((n - min) / (max - min)) * (h - 50);
  const path = (field: "actual" | "prediction" | "score") =>
    points
      .map(
        (p, i) =>
          `${i ? "L" : "M"}${px(i).toFixed(2)},${py(p[field] ?? 0).toFixed(2)}`,
      )
      .join(" ");
  return (
    <div className="chart">
      <div className="chart-legend">
        <span>
          <i className="legend actual" />
          {anomaly ? "Anomaly score" : "Observed demand"}
        </span>
        {anomaly ? null : (
          <span>
            <i className="legend predicted" />
            Model prediction
          </span>
        )}
        <Badge tone="neutral">
          {anomaly ? "Computed scores" : "Holdout · unseen dates"}
        </Badge>
      </div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={
          anomaly
            ? "Anomaly scores over time"
            : "Observed demand and model predictions on chronological holdout data"
        }
      >
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i}>
            <line
              x1={pad}
              y1={py((max * i) / 4)}
              x2={w - 20}
              y2={py((max * i) / 4)}
              className="grid-line"
            />
            <text x={pad - 10} y={py((max * i) / 4) + 4} textAnchor="end">
              {Math.round((max * i) / 4)}
            </text>
          </g>
        ))}
        <path d={path(anomaly ? "score" : "actual")} className="actual-line" />
        {!anomaly ? (
          <path d={path("prediction")} className="prediction-line" />
        ) : null}
        {points.map((p, i) =>
          anomaly && p.flag ? (
            <circle
              key={i}
              cx={px(i)}
              cy={py(p.score ?? 0)}
              r={4}
              className="anomaly-dot"
            >
              <title>
                {p.day}: {p.score?.toFixed(2)}
              </title>
            </circle>
          ) : null,
        )}
        {[
          0,
          Math.floor(points.length / 3),
          Math.floor((points.length * 2) / 3),
          points.length - 1,
        ].map((i, j) => (
          <text
            key={j}
            x={px(i)}
            y={h - 5}
            textAnchor={j === 0 ? "start" : j === 3 ? "end" : "middle"}
          >
            {points[i].day.slice(5)}
          </text>
        ))}
      </svg>
    </div>
  );
}
