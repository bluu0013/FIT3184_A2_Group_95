
import unittest
from unittest.mock import patch

import _paths
from ecoguard_common import search


class TestSearchLocal(unittest.TestCase):

    @patch("ecoguard_common.search.present")
    @patch("ecoguard_common.search.db.scan_ready")
    def test_search_tags(self, mock_scan, mock_present):

        mock_scan.return_value = [
            {
                "file_id": "file001",
                "tags": {"fox": 3, "cat": 2},
                "created_at": "2026-10-20T10:00:00+00:00"
            },
            {
                "file_id": "file002",
                "tags": {"fox": 1, "cat": 1},
                "created_at": "2026-10-21T10:00:00+00:00"
            },
            {
                "file_id": "file003",
                "tags": {"dog": 2},
                "created_at": "2026-10-22T10:00:00+00:00"
            }
        ]

        mock_present.side_effect = lambda item: item

        results = search.find_by_tags({
            "fox": 2,
            "cat": 1
        })

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file_id"], "file001")

    # Lost pet ranking 
    @patch("ecoguard_common.search.present")
    @patch("ecoguard_common.search.db.scan_ready")
    def test_lost_pet_ranking(self, mock_scan, mock_present):

        mock_scan.return_value = [
            {
                "file_id": "file001",
                "tags": {"cat": 1, "ginger": 1},
                "created_at": "2026-10-20T10:00:00+00:00"
            },
            {
                "file_id": "file002",
                "tags": {"cat": 1},
                "created_at": "2026-10-22T10:00:00+00:00"
            },
            {
                "file_id": "file003",
                "tags": {"dog": 1, "ginger": 1},
                "created_at": "2026-10-23T10:00:00+00:00"
            }
        ]

        mock_present.side_effect = lambda item: item

        results = search.find_lost_pet(
            species=["cat"],
            extra_tags=["ginger"],
            days=14
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["file_id"], "file001")
        self.assertEqual(results[1]["file_id"], "file002")


if __name__ == "__main__":
    unittest.main()
