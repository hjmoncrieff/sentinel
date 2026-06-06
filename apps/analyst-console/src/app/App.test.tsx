import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App shell bootstrap", () => {
  it("renders the analyst-console application shell", () => {
    render(<App />);

    expect(
      screen.getByRole("banner", { name: /sentinel analyst console/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: /analyst workspace/i }),
    ).toBeInTheDocument();
  });
});
