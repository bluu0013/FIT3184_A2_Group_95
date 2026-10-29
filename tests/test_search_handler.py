
import json
import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path

import _paths

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "services/aws/functions/search/app.py"

spec = importlib.util.spec_from_file_location("search_app", APP_PATH)
search_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search_app)


class TestSearchHandler(unittest.TestCase):

    # Tag search and logic
    @patch.object(search_app.search, "find_by_tags")
    def test_search_tags_endpoint(self, mock_find):
        mock_find.return_value = [
            {"file_id": "file001", "tags": {"fox": 3, "cat": 2}}
        ]

        event = {
            "routeKey": "POST /search/tags",
            "body": json.dumps({
                "tags": {"fox": 2, "cat": 1}
            })
        }

        response = search_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])
        self.assertEqual(body["results"][0]["file_id"], "file001")

        mock_find.assert_called_once_with(
            {"fox": 2, "cat": 1}, None, None
        )

    # Thumbnail URL lookup
    @patch.object(search_app.storage, "presign_get")
    @patch.object(search_app.db, "get_file")
    @patch.object(search_app.urls, "file_id_from_url")
    def test_thumbnail_lookup(self, mock_file_id, mock_get_file, mock_presign):

        mock_file_id.return_value = "file001"

        mock_get_file.return_value = {
            "file_id": "file001",
            "s3_key": "uploads/file001.jpg"
        }

        mock_presign.return_value = "https://example.com/full-image.jpg"

        event = {
            "routeKey": "POST /search/thumbnail",
            "body": json.dumps({
                "thumbnail_url": "https://example.com/thumbs/file001.jpg"
            })
        }

        response = search_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(body["file_id"], "file001")
        self.assertEqual(
            body["url"],
            "https://example.com/full-image.jpg"
        )

        mock_get_file.assert_called_once_with("file001")
        mock_presign.assert_called_once_with("uploads/file001.jpg")

    # Search by uploaded file
    @patch.object(search_app.search, "find_by_tags")
    @patch.object(search_app.inference, "detect")
    def test_search_by_file(self, mock_detect, mock_find):

        mock_detect.return_value = {
            "counts": {"fox": 2}
        }

        mock_find.return_value = [
            {
                "file_id": "file001",
                "tags": {"fox": 3}
            }
        ]

        event = {
            "routeKey": "POST /search/by-file",
            "headers": {
                "authorization": "Bearer test-token"
            },
            "body": json.dumps({
                "image_base64": "aGVsbG8="
            })
        }

        response = search_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(body["detected_tags"], {"fox": 2})
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["file_id"], "file001")

        mock_find.assert_called_once_with({"fox": 1})
        mock_detect.assert_called_once()

    # Lost pet search
    @patch.object(search_app.search, "find_lost_pet")
    def test_lost_pet_search(self, mock_find):

        mock_find.return_value = [
            {
                "file_id": "file001",
                "tags": {"cat": 1, "ginger": 1}
            }
        ]

        event = {
            "routeKey": "POST /search/lost-pet",
            "body": json.dumps({
                "tags": ["cat", "ginger"],
                "days": 14
            })
        }

        response = search_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(body["detected_tags"], {})
        self.assertEqual(body["results"][0]["file_id"], "file001")

        mock_find.assert_called_once_with(
            ["cat"], ["ginger"], 14
        )


if __name__ == "__main__":
    unittest.main()
