import { getApiErrorMessage } from "@/lib/apiError";

describe("getApiErrorMessage", () => {
  it("normalizes FastAPI validation detail arrays", () => {
    expect(
      getApiErrorMessage(
        {
          response: {
            data: {
              detail: [
                { loc: ["body", "username"], msg: "用戶名稱格式錯誤" },
                { loc: ["body", "email"], msg: "電子郵件格式錯誤" },
              ],
            },
          },
        },
        "註冊失敗",
      ),
    ).toBe("用戶名稱格式錯誤；電子郵件格式錯誤");
  });
});
