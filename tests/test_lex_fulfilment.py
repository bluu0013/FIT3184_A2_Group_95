
import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path

import _paths

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "services/aws/functions/lex_fulfilment/app.py"

spec = importlib.util.spec_from_file_location(
    "lex_fulfilment_app", APP_PATH
)
lex_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lex_app)


class TestLexFulfilment(unittest.TestCase):

    @patch.object(lex_app.search, "find_by_tags")
    def test_find_species(self, mock_find):

        mock_find.return_value = [
            {
                "file_id": "file001",
                "tags": {"fox": 2},
                "thumb_url": "https://example.com/fox-thumb.jpg",
                "url": "https://example.com/fox.jpg"
            }
        ]

        event = {
            "sessionState": {
                "intent": {
                    "name": "FindSpecies",
                    "slots": {
                        "Species": {
                            "value": {
                                "interpretedValue": "fox"
                            }
                        },
                        "MinCount": {
                            "value": {
                                "interpretedValue": "2"
                            }
                        }
                    }
                }
            }
        }

        response = lex_app.handler(event, None)

        self.assertEqual(
            response["sessionState"]["intent"]["state"],
            "Fulfilled"
        )

        self.assertIn(
            "fox",
            response["messages"][0]["content"]
        )

        mock_find.assert_called_once_with(
            {"fox": 2}, None, None
        )

    
    @patch.object(lex_app.search, "find_lost_pet")
    def test_lost_pet(self, mock_find):

        mock_find.return_value = [
            {
                "file_id": "file002",
                "tags": {"cat": 1, "ginger": 1},
                "thumb_url": "https://example.com/cat-thumb.jpg",
                "url": "https://example.com/cat.jpg"
            }
        ]

        event = {
            "sessionState": {
                "intent": {
                    "name": "LostPet",
                    "slots": {
                        "Species": {
                            "value": {
                                "interpretedValue": "cat"
                            }
                        },
                        "Colour": {
                            "value": {
                                "interpretedValue": "ginger"
                            }
                        },
                        "Breed": None
                    }
                }
            }
        }

        response = lex_app.handler(event, None)

        self.assertEqual(
            response["sessionState"]["intent"]["state"],
            "Fulfilled"
        )

        self.assertIn(
            "ginger cat",
            response["messages"][0]["content"]
        )

        self.assertIn(
            "https://example.com/cat-thumb.jpg",
            response["messages"][0]["content"]
        )

        mock_find.assert_called_once_with(
            ["cat"], ["ginger"]
        )

    # Date filtering
    @patch.object(lex_app.search, "find_by_tags")
    def test_find_species_with_date(self, mock_find):

        mock_find.return_value = []

        event = {
            "sessionState": {
                "intent": {
                    "name": "FindSpecies",
                    "slots": {
                        "Species": {
                            "value": {
                                "interpretedValue": "fox"
                            }
                        },
                        "MinCount": None,
                        "Date": {
                            "value": {
                                "interpretedValue": "2026-10-25"
                            }
                        }
                    }
                }
            }
        }

        response = lex_app.handler(event, None)

        self.assertEqual(
            response["sessionState"]["intent"]["state"],
            "Fulfilled"
        )

        self.assertIn(
            "could not find any files",
            response["messages"][0]["content"]
        )

        mock_find.assert_called_once_with(
            {"fox": 1},
            "2026-10-25T00:00:00+00:00",
            "2026-10-26T00:00:00+00:00"
        )




if __name__ == "__main__":
    unittest.main()
