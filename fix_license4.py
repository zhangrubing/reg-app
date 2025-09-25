from pathlib import Path
path = Path("backend/routers/licenses.py")
text = path.read_text(encoding="utf-8")
needle = """
    items = [_row_to_license(row) for row in rows]
    headers = ["ID", "SN", "Activation ID", "Product", "Status", "Issued At", "Expires At", "Revoked At"]
    lines = [",".join(headers)]
    for item in items:
        lines.append(
            ",".join(
                [
                    str(item.get("id", "")),
                    item.get("sn", "") or "",
                    str(item.get("activation_id") or ""),
                    item.get("product_name") or "",
                    item.get("status", ""),
                    item.get("issued_at") or "",
                    item.get("expires_at") or "",
                    item.get("revoked_at") or "",
                ]
            )
        )

    csv_content = "
".join(lines)
    csv_bytes = csv_content.encode("utf-8-sig")
    filename = f"licenses-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
"""
replacement = """
    items = [_row_to_license(row) for row in rows]
    headers = ["ID", "SN", "Activation ID", "Product", "Status", "Issued At", "Expires At", "Revoked At"]
    lines = [",".join(headers)]
    for item in items:
        lines.append(
            ",".join(
                [
                    str(item.get("id", "")),
                    item.get("sn", "") or "",
                    str(item.get("activation_id") or ""),
                    item.get("product_name") or "",
                    item.get("status", ""),
                    item.get("issued_at") or "",
                    item.get("expires_at") or "",
                    item.get("revoked_at") or "",
                ]
            )
        )

    csv_content = "\n".join(lines)
    csv_bytes = csv_content.encode("utf-8-sig")
    filename = f"licenses-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
"""
if needle not in text:
    raise SystemExit('Target block not found; aborting to avoid corrupting file.')
text = text.replace(needle, replacement)
path.write_text(text, encoding="utf-8")
