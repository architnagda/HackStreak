/**
 * Formats an ISO date string from the backend into user's local real time.
 * Handles UTC strings with or without trailing 'Z'.
 */
export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "";
  
  // Ensure UTC parsing if no timezone is provided
  let isoStr = dateStr;
  if (!isoStr.endsWith("Z") && !isoStr.includes("+") && !isoStr.includes("-", 10)) {
    isoStr += "Z";
  }

  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return dateStr;
  }
}

export function formatTimeOnly(dateStr?: string | null): string {
  if (!dateStr) return "";
  let isoStr = dateStr;
  if (!isoStr.endsWith("Z") && !isoStr.includes("+") && !isoStr.includes("-", 10)) {
    isoStr += "Z";
  }

  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return dateStr;
  }
}

export function formatRelativeTime(dateStr?: string | null): string {
  if (!dateStr) return "";
  let isoStr = dateStr;
  if (!isoStr.endsWith("Z") && !isoStr.includes("+") && !isoStr.includes("-", 10)) {
    isoStr += "Z";
  }

  try {
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? "s" : ""} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;

    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}
