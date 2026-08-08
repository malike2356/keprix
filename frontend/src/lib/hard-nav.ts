/** Force a full document navigation.

Next.js App Router soft navigation can stick (link clicks preventDefault then
router.push becomes a no-op). Prefer a real anchor click over location.assign;
assign is unreliable from some non-gesture contexts in Chromium.
*/
export function hardNavigate(href: string): void {
  if (typeof window === "undefined") return;
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.setAttribute("data-keprix-hard-nav", "1");
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}
