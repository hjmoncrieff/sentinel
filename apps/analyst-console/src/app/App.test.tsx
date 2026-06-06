import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loadConsoleData } from "@/lib/api/load-console-data";
import { App } from "./App";

vi.mock("@/lib/api/load-console-data", () => ({
  loadConsoleData: vi.fn(),
}));

describe("App shell bootstrap", () => {
  beforeEach(() => {
    vi.mocked(loadConsoleData).mockResolvedValue([
      {
        event_id: "evt-1",
        headline: "Alpha review item",
        country: "Colombia",
        review_priority: "high",
      },
    ]);
  });

  it("renders the global rail, console search, and triad workspace", async () => {
    render(<App />);

    expect(
      await screen.findByRole("banner", { name: /sentinel analyst console/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: /global workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("search", { name: /console search/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: /analyst workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("complementary", { name: /review queue/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /event brief/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /review actions/i }),
    ).toBeInTheDocument();
  });
});
