import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Chart, Pagination } from "./components";
import { RunTable } from "./views";

afterEach(cleanup);
describe("operational evidence", () => {
  it("does not fabricate an empty chart", () => {
    render(<Chart points={[]} />);
    expect(screen.getByText("No chart evidence")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
  it("labels real computed chart evidence", () => {
    render(
      <Chart
        points={[
          {
            day: "2025-06-01",
            sku: "a",
            location: "b",
            actual: 10,
            prediction: 11,
          },
        ]}
      />,
    );
    expect(screen.getByRole("img")).toHaveAttribute(
      "aria-label",
      expect.stringContaining("holdout"),
    );
    expect(screen.getByText("Model prediction")).toBeInTheDocument();
  });
  it("disables page changes outside available evidence", () => {
    const change = vi.fn();
    render(<Pagination total={26} offset={0} onChange={change} />);
    expect(screen.getByLabelText("Previous page")).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Next page"));
    expect(change).toHaveBeenCalledWith(25);
  });
  it("shows an empty registry instead of mocked versions", () => {
    render(<RunTable runs={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("No model versions yet")).toBeInTheDocument();
  });
});
