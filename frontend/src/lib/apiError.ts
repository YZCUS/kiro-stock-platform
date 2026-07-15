export function getApiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (
          item &&
          typeof item === "object" &&
          "msg" in item &&
          typeof item.msg === "string"
        ) {
          return item.msg;
        }
        return null;
      })
      .filter((message): message is string => Boolean(message));

    if (messages.length > 0) return messages.join("；");
  }

  return error instanceof Error && error.message ? error.message : fallback;
}
