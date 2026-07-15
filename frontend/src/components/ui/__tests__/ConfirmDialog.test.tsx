import { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ConfirmDialog from "@/components/ui/ConfirmDialog";

function DialogHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        刪除標的
      </button>
      <ConfirmDialog
        isOpen={open}
        title="確認刪除"
        message="此操作無法復原"
        onConfirm={() => setOpen(false)}
        onCancel={() => setOpen(false)}
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("closes with Escape and restores focus to the opener", async () => {
    render(<DialogHarness />);
    const opener = screen.getByRole("button", { name: "刪除標的" });

    opener.focus();
    fireEvent.click(opener);
    expect(screen.getByRole("alertdialog")).toHaveAttribute(
      "aria-modal",
      "true",
    );

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
      expect(opener).toHaveFocus();
    });
  });
});
