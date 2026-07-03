export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatList(values?: string[] | null): string {
  if (!values || values.length === 0) {
    return "Not specified";
  }
  return values.join(", ");
}

export function compactId(value: string): string {
  return value.replace(/^project_/, "").slice(0, 8);
}
