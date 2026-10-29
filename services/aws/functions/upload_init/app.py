"""POST /upload/init: checksum dedup and presigned upload URL. Owner: Member A."""
import os

from ecoguard_common import db, responses, storage, urls

ALLOWED_TYPES = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "video/quicktime": "video",
    "video/webm": "video",
}
MAX_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))


def _init(event):
    body = responses.json_body(event)
    file_id = str(body.get("sha256", "")).lower()
    content_type = body.get("content_type")
    size = body.get("size")

    if not urls.is_sha256(file_id):
        raise ValueError("sha256 must be 64 hex characters")
    if content_type not in ALLOWED_TYPES:
        raise ValueError("content_type must be one of: " + ", ".join(sorted(ALLOWED_TYPES)))
    if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_BYTES:
        raise ValueError(f"size must be between 1 and {MAX_BYTES} bytes")

    key = urls.media_key(file_id, body.get("filename"))
    item = {
        "file_id": file_id,
        "type": ALLOWED_TYPES[content_type],
        "filename": urls.safe_filename(body.get("filename")),
        "content_type": content_type,
        "size": size,
        "owner": responses.claims(event).get("sub", "unknown"),
        "s3_key": key,
        "tags": {},
        "status": "pending",
        "created_at": db.now_iso(),
    }

    created = db.create_pending(item)
    if not created:
        existing = db.get_file(file_id)
        status = (existing or {}).get("status")
        if status in ("failed", "rejected"):
            db.put(item)  # allow a retry of a file that never became ready
            created = True
        elif status == "pending":
            created = True  # an earlier upload never finished; same content, so just hand out a new URL
        else:
            return {
                "duplicate": True,
                "file_id": file_id,
                "status": (existing or {}).get("status"),
                "url": storage.presign_get((existing or {}).get("s3_key", key)),
            }

    return {
        "duplicate": False,
        "file_id": file_id,
        "upload_url": storage.presign_put(key, content_type),
        "required_headers": {"Content-Type": content_type},
    }


def handler(event, context):
    return responses.run(_init, event)
