"""Handler tests for Member A's Lambdas with db, storage, inference and notify mocked out."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

import _paths  # noqa: F401  (puts the shared layer on sys.path)

from ecoguard_common import inference

FUNCTIONS = Path(__file__).resolve().parents[1] / "services" / "aws" / "functions"
SHA = "a" * 64


def load(name):
    spec = importlib.util.spec_from_file_location(f"fn_{name}", FUNCTIONS / name / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def api_event(body, email=None):
    claims = {"sub": "user-1"}
    if email:
        claims["email"] = email
    return {
        "body": json.dumps(body),
        "requestContext": {"authorizer": {"jwt": {"claims": claims}}},
    }


def s3_event(key):
    return {"detail": {"object": {"key": key}}}


class UploadInitTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("upload_init")
        self.body = {"filename": "fox.jpg", "content_type": "image/jpeg", "sha256": SHA, "size": 10}

    def call(self, body):
        return self.mod.handler(api_event(body), None)

    def test_new_file_returns_presigned_put(self):
        with mock.patch.object(self.mod.db, "create_pending", return_value=True) as create, \
                mock.patch.object(self.mod.storage, "presign_put", return_value="https://put"):
            resp = self.call(self.body)
        out = json.loads(resp["body"])
        self.assertEqual(resp["statusCode"], 200)
        self.assertFalse(out["duplicate"])
        self.assertEqual(out["upload_url"], "https://put")
        item = create.call_args.args[0]
        self.assertEqual(item["status"], "pending")
        self.assertEqual(item["s3_key"], f"media/{SHA}/fox.jpg")
        self.assertEqual(item["owner"], "user-1")

    def test_duplicate_is_reported_not_uploaded(self):
        existing = {"status": "ready", "s3_key": f"media/{SHA}/fox.jpg"}
        with mock.patch.object(self.mod.db, "create_pending", return_value=False), \
                mock.patch.object(self.mod.db, "get_file", return_value=existing), \
                mock.patch.object(self.mod.storage, "presign_get", return_value="https://get"):
            out = json.loads(self.call(self.body)["body"])
        self.assertTrue(out["duplicate"])
        self.assertEqual(out["status"], "ready")
        self.assertNotIn("upload_url", out)

    def test_failed_file_can_be_retried(self):
        with mock.patch.object(self.mod.db, "create_pending", return_value=False), \
                mock.patch.object(self.mod.db, "get_file", return_value={"status": "failed"}), \
                mock.patch.object(self.mod.db, "put") as put, \
                mock.patch.object(self.mod.storage, "presign_put", return_value="https://put"):
            out = json.loads(self.call(self.body)["body"])
        self.assertFalse(out["duplicate"])
        put.assert_called_once()

    def test_abandoned_pending_upload_gets_a_fresh_url(self):
        with mock.patch.object(self.mod.db, "create_pending", return_value=False), \
                mock.patch.object(self.mod.db, "get_file", return_value={"status": "pending"}), \
                mock.patch.object(self.mod.db, "put") as put, \
                mock.patch.object(self.mod.storage, "presign_put", return_value="https://put"):
            out = json.loads(self.call(self.body)["body"])
        self.assertFalse(out["duplicate"])
        self.assertEqual(out["upload_url"], "https://put")
        put.assert_not_called()

    def test_bad_input_is_400(self):
        for patch in ({"sha256": "xyz"}, {"content_type": "text/plain"}, {"size": 0}, {"size": True}):
            resp = self.call({**self.body, **patch})
            self.assertEqual(resp["statusCode"], 400, patch)

    def test_hash_is_case_insensitive(self):
        with mock.patch.object(self.mod.db, "create_pending", return_value=True) as create, \
                mock.patch.object(self.mod.storage, "presign_put", return_value="u"):
            self.call({**self.body, "sha256": SHA.upper()})
        self.assertEqual(create.call_args.args[0]["file_id"], SHA)


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("ingest")
        self.key = f"media/{SHA}/fox.jpg"

    def test_unknown_file_is_ignored(self):
        with mock.patch.object(self.mod.db, "get_file", return_value=None), \
                mock.patch.object(self.mod.storage, "sha256_of") as digest:
            out = self.mod.handler(s3_event(self.key), None)
        self.assertEqual(out, {"skipped": True})
        digest.assert_not_called()

    def test_checksum_mismatch_is_rejected_and_object_deleted(self):
        with mock.patch.object(self.mod.db, "get_file", return_value={"type": "image"}), \
                mock.patch.object(self.mod.storage, "sha256_of", return_value="b" * 64), \
                mock.patch.object(self.mod.storage, "delete_keys") as delete, \
                mock.patch.object(self.mod.db, "update") as update, \
                mock.patch.object(self.mod.inference, "detect") as detect:
            out = self.mod.handler(s3_event(self.key), None)
        self.assertEqual(out, {"rejected": True})
        delete.assert_called_once_with([self.key])
        self.assertEqual(update.call_args.kwargs["status"], "rejected")
        detect.assert_not_called()

    def test_success_stores_tags_and_alerts(self):
        result = {"counts": {"fox": 2}, "model_version": "v1"}
        with mock.patch.object(self.mod.db, "get_file", return_value={"type": "video"}), \
                mock.patch.object(self.mod.storage, "sha256_of", return_value=SHA), \
                mock.patch.object(self.mod.storage, "presign_get", return_value="https://get"), \
                mock.patch.object(self.mod.inference, "detect", return_value=result) as detect, \
                mock.patch.object(self.mod.db, "update") as update, \
                mock.patch.object(self.mod.notify, "publish_tags") as publish:
            out = self.mod.handler(s3_event(self.key), None)
        self.assertEqual(out["tags"], {"fox": 2})
        self.assertEqual(detect.call_args.kwargs["media_type"], "video")
        self.assertEqual(update.call_args.kwargs["status"], "ready")
        publish.assert_called_once_with(SHA, {"fox": 2})

    def test_inference_failure_marks_failed_and_reraises(self):
        with mock.patch.object(self.mod.db, "get_file", return_value={"type": "image"}), \
                mock.patch.object(self.mod.storage, "sha256_of", return_value=SHA), \
                mock.patch.object(self.mod.storage, "presign_get", return_value="u"), \
                mock.patch.object(self.mod.inference, "detect", side_effect=inference.InferenceError("down")), \
                mock.patch.object(self.mod.db, "update") as update, \
                mock.patch.object(self.mod.notify, "publish_tags") as publish:
            with self.assertRaises(inference.InferenceError):
                self.mod.handler(s3_event(self.key), None)
        self.assertEqual(update.call_args.kwargs["status"], "failed")
        publish.assert_not_called()


class SubscriptionsTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("subscriptions")

    def test_defaults_to_signed_in_email_and_normalises_tags(self):
        with mock.patch.object(self.mod.notify, "subscribe_email") as sub:
            resp = self.mod.handler(api_event({"tags": ["Feral  Pig"]}, email="me@example.com"), None)
        self.assertEqual(resp["statusCode"], 200)
        sub.assert_called_once_with("me@example.com", ["feral pig"])

    def test_rejects_bad_email_and_missing_tags(self):
        with mock.patch.object(self.mod.notify, "subscribe_email") as sub:
            bad_email = self.mod.handler(api_event({"tags": ["fox"], "email": "nope"}), None)
            no_tags = self.mod.handler(api_event({"email": "a@b.co"}), None)
        self.assertEqual(bad_email["statusCode"], 400)
        self.assertEqual(no_tags["statusCode"], 400)
        sub.assert_not_called()


class ThumbnailTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("thumbnail")

    def test_make_thumbnail_keeps_aspect_ratio_and_never_upscales(self):
        import io
        from PIL import Image

        def jpeg(w, h):
            buf = io.BytesIO()
            Image.new("RGB", (w, h), "red").save(buf, "JPEG")
            return buf.getvalue()

        big = Image.open(io.BytesIO(self.mod.make_thumbnail(jpeg(1000, 500), max_edge=256)))
        self.assertEqual(big.size, (256, 128))
        small = Image.open(io.BytesIO(self.mod.make_thumbnail(jpeg(100, 50), max_edge=256)))
        self.assertEqual(small.size, (100, 50))

    def test_videos_are_skipped(self):
        with mock.patch.object(self.mod.db, "get_file", return_value={"type": "video"}), \
                mock.patch.object(self.mod.storage, "get_bytes") as get:
            out = self.mod.handler(s3_event(f"media/{SHA}/clip.mp4"), None)
        self.assertEqual(out, {"skipped": True})
        get.assert_not_called()


class NotifyTests(unittest.TestCase):
    def test_publish_sets_string_array_tags_attribute(self):
        from ecoguard_common import notify

        client = mock.Mock()
        with mock.patch.object(notify, "_sns", return_value=client), \
                mock.patch.dict("os.environ", {"ALERTS_TOPIC_ARN": "arn:topic"}):
            notify.publish_tags(SHA, {"fox": 2, "cat": 1})
        attrs = client.publish.call_args.kwargs["MessageAttributes"]["tags"]
        self.assertEqual(attrs["DataType"], "String.Array")
        self.assertEqual(json.loads(attrs["StringValue"]), ["cat", "fox"])

    def test_no_species_means_no_alert(self):
        from ecoguard_common import notify

        client = mock.Mock()
        with mock.patch.object(notify, "_sns", return_value=client), \
                mock.patch.dict("os.environ", {"ALERTS_TOPIC_ARN": "arn:topic"}):
            notify.publish_tags(SHA, {})
        client.publish.assert_not_called()


class InferenceKeyTests(unittest.TestCase):
    def setUp(self):
        inference._key_cache = None
        self.addCleanup(setattr, inference, "_key_cache", None)

    def _env(self, **env):
        base = {"INFERENCE_API_KEY": "", "INFERENCE_API_KEY_PARAM": ""}
        return mock.patch.dict("os.environ", {**base, **env})

    def test_key_comes_from_ssm_once_and_is_cached(self):
        ssm = mock.Mock()
        ssm.get_parameter.return_value = {"Parameter": {"Value": "s3cret"}}
        with self._env(INFERENCE_API_KEY_PARAM="/ecoguard/key"),                 mock.patch("boto3.client", return_value=ssm) as client:
            self.assertEqual(inference._api_key(), "s3cret")
            self.assertEqual(inference._api_key(), "s3cret")
        client.assert_called_once_with("ssm")
        ssm.get_parameter.assert_called_once_with(Name="/ecoguard/key", WithDecryption=True)

    def test_local_override_skips_ssm(self):
        with self._env(INFERENCE_API_KEY="dev-key", INFERENCE_API_KEY_PARAM="/ecoguard/key"),                 mock.patch("boto3.client") as client:
            self.assertEqual(inference._api_key(), "dev-key")
        client.assert_not_called()

    def test_unreadable_parameter_is_an_inference_error(self):
        ssm = mock.Mock()
        ssm.get_parameter.side_effect = RuntimeError("AccessDenied")
        with self._env(INFERENCE_API_KEY_PARAM="/ecoguard/key"),                 mock.patch("boto3.client", return_value=ssm):
            with self.assertRaises(inference.InferenceError):
                inference._api_key()

    def test_rejected_key_is_dropped_so_a_rotated_key_is_picked_up(self):
        import urllib.error

        inference._key_cache = "stale"
        rejected = urllib.error.HTTPError("https://run.example/detect", 401, "Unauthorized", {}, None)
        with self._env(INFERENCE_URL="https://run.example"), \
                mock.patch("urllib.request.urlopen", side_effect=rejected):
            with self.assertRaises(inference.InferenceError):
                inference.detect(url="https://x")
        self.assertIsNone(inference._key_cache)

    def test_user_token_requests_never_touch_ssm(self):
        response = mock.MagicMock()
        response.__enter__.return_value = io_json({"counts": {}})
        with self._env(INFERENCE_URL="https://run.example", INFERENCE_API_KEY_PARAM="/ecoguard/key"),                 mock.patch("boto3.client") as client,                 mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            inference.detect(url="https://x", token="jwt")
        client.assert_not_called()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer jwt")
        self.assertIsNone(request.get_header("X-api-key"))


def io_json(data):
    import io

    return io.StringIO(json.dumps(data))


if __name__ == "__main__":
    unittest.main()
