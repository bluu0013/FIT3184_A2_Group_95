
import json
import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path

import _paths

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "services/aws/functions/manage/app.py"

spec = importlib.util.spec_from_file_location("manage_app", APP_PATH)
manage_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage_app)


class TestManageHandler(unittest.TestCase):

    @patch.object(manage_app.notify, "publish_tags")
    @patch.object(manage_app.db, "update")
    @patch.object(manage_app.db, "get_file")
    @patch.object(manage_app.urls, "file_id_from_url")
    def test_bulk_add_tags(
        self, mock_url, mock_get, mock_update, mock_notify
    ):
        mock_url.side_effect = ["file001", "file002"]

        mock_get.side_effect = [
            {
                "file_id": "file001",
                "tags": {"cat": 1}
            },
            {
                "file_id": "file002",
                "tags": {"dog": 1}
            }
        ]

        event = {
            "routeKey": "POST /tags",
            "body": json.dumps({
                "urls": [
                    "https://example.com/file001.jpg",
                    "https://example.com/file002.jpg"
                ],
                "operation": 1,
                "tags": {"fox": 2}
            })
        }

        response = manage_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(
            body["updated"],
            ["file001", "file002"]
        )

        self.assertEqual(body["not_found"], [])

        self.assertEqual(mock_update.call_count, 2)
        self.assertEqual(mock_notify.call_count, 2)

        mock_update.assert_any_call(
            "file001",
            tags={"cat": 1, "fox": 2}
        )

        mock_update.assert_any_call(
            "file002",
            tags={"dog": 1, "fox": 2}
        )


    @patch.object(manage_app.notify, "publish_tags")
    @patch.object(manage_app.db, "update")
    @patch.object(manage_app.db, "get_file")
    @patch.object(manage_app.urls, "file_id_from_url")
    def test_bulk_remove_tags(
        self, mock_url, mock_get, mock_update, mock_notify
    ):
        mock_url.side_effect = ["file001", "file002"]

        mock_get.side_effect = [
            {
                "file_id": "file001",
                "tags": {"cat": 1, "fox": 2}
            },
            {
                "file_id": "file002",
                "tags": {"dog": 1, "fox": 3}
            }
        ]

        event = {
            "routeKey": "POST /tags",
            "body": json.dumps({
                "urls": [
                    "https://example.com/file001.jpg",
                    "https://example.com/file002.jpg"
                ],
                "operation": 0,
                "tags": {"fox": 1}
            })
        }

        response = manage_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(
            body["updated"],
            ["file001", "file002"]
        )

        self.assertEqual(body["not_found"], [])

        mock_update.assert_any_call(
            "file001",
            tags={"cat": 1}
        )

        mock_update.assert_any_call(
            "file002",
            tags={"dog": 1}
        )

        self.assertEqual(mock_update.call_count, 2)
        mock_notify.assert_not_called()

    
    @patch.object(manage_app.db, "delete")
    @patch.object(manage_app.storage, "delete_keys")
    @patch.object(manage_app.db, "get_file")
    @patch.object(manage_app.urls, "file_id_from_url")
    def test_bulk_delete(
        self, mock_url, mock_get, mock_storage, mock_delete
    ):
        mock_url.side_effect = ["file001", "file002"]

        mock_get.side_effect = [
            {
                "file_id": "file001",
                "s3_key": "uploads/file001.jpg",
                "thumb_key": "thumbnails/file001.jpg"
            },
            {
                "file_id": "file002",
                "s3_key": "uploads/file002.jpg",
                "thumb_key": "thumbnails/file002.jpg"
            }
        ]

        event = {
            "routeKey": "POST /files/delete",
            "body": json.dumps({
                "urls": [
                    "https://example.com/file001.jpg",
                    "https://example.com/file002.jpg"
                ]
            })
        }

        response = manage_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(
            body["deleted"],
            ["file001", "file002"]
        )

        self.assertEqual(body["not_found"], [])

        mock_storage.assert_any_call([
            "uploads/file001.jpg",
            "thumbnails/file001.jpg"
        ])

        mock_storage.assert_any_call([
            "uploads/file002.jpg",
            "thumbnails/file002.jpg"
        ])

        mock_delete.assert_any_call("file001")
        mock_delete.assert_any_call("file002")

        self.assertEqual(mock_storage.call_count, 2)
        self.assertEqual(mock_delete.call_count, 2)



if __name__ == "__main__":
    unittest.main()
