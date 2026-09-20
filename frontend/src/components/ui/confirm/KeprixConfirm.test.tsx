import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { KeprixConfirmHost, keprixConfirm } from "@/components/ui/confirm/KeprixConfirm";

afterEach(() => {
  cleanup();
});

describe("KeprixConfirm", () => {
  it("resolves true from the named confirmation action", async () => {
    render(<KeprixConfirmHost />);
    const result = keprixConfirm({
      title: "Delete conversation?",
      confirmLabel: "Delete conversation",
      destructive: true,
    });

    fireEvent.click(await screen.findByRole("button", { name: "Delete conversation" }));
    await expect(result).resolves.toBe(true);
  });

  it("requires an exact typed match", async () => {
    render(<KeprixConfirmHost />);
    const result = keprixConfirm({
      title: "Restart engine?",
      confirmLabel: "Restart engine",
      requireTypedMatch: "RESTART",
    });

    const action = await screen.findByRole("button", { name: "Restart engine" });
    expect(action).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Type RESTART to confirm"), { target: { value: "RESTART" } });
    expect(action).toBeEnabled();
    fireEvent.click(action);
    await expect(result).resolves.toBe(true);
  });
});
