export function getSafeRedirectPath(
  value: string | null | undefined,
  fallback = "/",
): string {
  if (!value?.startsWith("/") || value.startsWith("//")) return fallback;

  try {
    const localOrigin = "https://local.invalid";
    const target = new URL(value, localOrigin);
    return target.origin === localOrigin
      ? `${target.pathname}${target.search}${target.hash}`
      : fallback;
  } catch {
    return fallback;
  }
}

export function buildLoginHref(pathname: string, search = ""): string {
  const currentPath = getSafeRedirectPath(`${pathname}${search}`);
  return `/login?redirect=${encodeURIComponent(currentPath)}`;
}

export function shouldRedirectUnauthorized(
  status: number | undefined,
  requestPath: string | undefined,
  currentPath: string,
): boolean {
  if (status !== 401) return false;
  if (currentPath === "/login" || currentPath === "/register") return false;
  return (
    requestPath !== "/api/v1/auth/login" &&
    requestPath !== "/api/v1/auth/register"
  );
}
