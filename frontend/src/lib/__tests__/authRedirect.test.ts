import {
  buildLoginHref,
  getSafeRedirectPath,
  shouldRedirectUnauthorized,
} from "@/lib/authRedirect";

describe("auth redirect helpers", () => {
  it("keeps a local route including its query string", () => {
    expect(buildLoginHref("/stocks", "?list=3")).toBe(
      "/login?redirect=%2Fstocks%3Flist%3D3",
    );
  });

  it("rejects external and protocol-relative redirects", () => {
    expect(getSafeRedirectPath("https://example.com", "/dashboard")).toBe(
      "/dashboard",
    );
    expect(getSafeRedirectPath("//example.com", "/dashboard")).toBe(
      "/dashboard",
    );
    expect(getSafeRedirectPath("/\\evil.example", "/dashboard")).toBe(
      "/dashboard",
    );
  });

  it("keeps login failures on the login page", () => {
    expect(
      shouldRedirectUnauthorized(401, "/api/v1/auth/login", "/login"),
    ).toBe(false);
    expect(
      shouldRedirectUnauthorized(401, "/api/v1/portfolio/", "/portfolio"),
    ).toBe(true);
  });
});
