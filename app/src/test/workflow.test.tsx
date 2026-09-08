import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import App from "../App";

describe("App workflow smoke", () => {
  it("supports keyboard-only discover and connect path", async () => {
    const user = userEvent.setup();
    render(<App />);

    const discoverButton = screen.getByRole("button", { name: /discover usb adapters/i });
    discoverButton.focus();
    expect(discoverButton).toHaveFocus();
    await user.keyboard("{Enter}");

    const connectButton = await screen.findByRole("button", { name: /connect/i });
    expect(connectButton).toBeEnabled();
  });
});
