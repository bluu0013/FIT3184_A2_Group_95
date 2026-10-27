"""Client for the GCP Cloud Run inference service (see services/gcp/inference)."""
import json
import os
import urllib.error
import urllib.request


class InferenceError(ConnectionError):
    """Raised when the inference service cannot be reached or returns an error."""


_key_cache = None


def _api_key():
    """Shared key for calls with no user token: SSM SecureString named by INFERENCE_API_KEY_PARAM.

    INFERENCE_API_KEY is only a local-development override. The SSM value is cached per container.
    """
    global _key_cache
    if _key_cache is None:
        direct = os.environ.get("INFERENCE_API_KEY")
        param = os.environ.get("INFERENCE_API_KEY_PARAM")
        if direct:
            _key_cache = direct
        elif param:
            import boto3

            try:
                _key_cache = boto3.client("ssm").get_parameter(Name=param, WithDecryption=True)[
                    "Parameter"
                ]["Value"]
            except Exception as exc:  # missing parameter or no permission
                raise InferenceError(f"cannot read API key from SSM parameter {param}") from exc
        else:
            _key_cache = ""
    return _key_cache


def detect(*, url=None, image_base64=None, media_type="image", token=None, timeout=25):
    """Call POST /detect.

    token: the caller's Cognito token to forward (user-initiated requests). When None the shared
    X-Api-Key from SSM is used (S3-triggered ingest has no user token).
    timeout: keep under 30 s for API Gateway paths; ingest may pass a larger value.
    """
    base = os.environ.get("INFERENCE_URL", "").rstrip("/")
    if not base:
        raise InferenceError("INFERENCE_URL is not configured")
    if not (url or image_base64):
        raise ValueError("url or image_base64 is required")

    payload = {"media_type": media_type}
    if url:
        payload["url"] = url
    if image_base64:
        payload["image_base64"] = image_base64

    headers = {"Content-Type": "application/json"}
    used_shared_key = False
    if token:
        headers["Authorization"] = "Bearer " + token
    else:
        key = _api_key()
        if key:
            headers["X-Api-Key"] = key
            used_shared_key = True

    request = urllib.request.Request(
        base + "/detect", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        global _key_cache
        if used_shared_key and exc.code in (401, 403):
            _key_cache = None  # the key may have been rotated in SSM: re-read it on the next call
        raise InferenceError(f"inference service returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise InferenceError(f"inference service unreachable: {exc}") from exc
