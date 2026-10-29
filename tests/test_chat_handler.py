
import json
import unittest
from unittest.mock import patch, MagicMock
import importlib.util
from pathlib import Path

import _paths

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "services/aws/functions/chat/app.py"

spec = importlib.util.spec_from_file_location(
    "chat_app", APP_PATH
)
chat_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat_app)


class TestChatHandler(unittest.TestCase):

    @patch.dict("os.environ", {
        "LEX_BOT_ID": "TESTBOT123",
        "LEX_BOT_ALIAS_ID": "TESTALIAS1",
        "LEX_LOCALE_ID": "en_US"
    })
    @patch.object(chat_app, "_client")
    def test_chat_message(self, mock_client):

        mock_lex = MagicMock()
        mock_client.return_value = mock_lex

        mock_lex.recognize_text.return_value = {
            "messages": [
                {
                    "contentType": "PlainText",
                    "content": "Found 2 fox images."
                }
            ],
            "sessionState": {
                "intent": {
                    "name": "FindSpecies"
                }
            }
        }

        event = {
            "routeKey": "POST /chat",
            "body": json.dumps({
                "text": "Find foxes",
                "session_id": "test-session-001"
            })
        }

        response = chat_app.handler(event, None)

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertEqual(
            body["messages"],
            ["Found 2 fox images."]
        )

        self.assertEqual(
            body["intent"],
            "FindSpecies"
        )

        self.assertEqual(
            body["session_id"],
            "test-session-001"
        )

        mock_lex.recognize_text.assert_called_once_with(
            botId="TESTBOT123",
            botAliasId="TESTALIAS1",
            localeId="en_US",
            sessionId="test-session-001",
            text="Find foxes"
        )

    
    @patch.object(chat_app, "_client")
    def test_empty_message(self, mock_client):
        event = {
            "routeKey": "POST /chat",
            "body": json.dumps({
                "text": "   "
            })
        }

        response = chat_app.handler(event, None)

        self.assertEqual(response["statusCode"], 400)
        mock_client.assert_not_called()



    @patch.dict(
        "os.environ",
        {
            "LEX_BOT_ID": "",
            "LEX_BOT_ALIAS_ID": ""
        }
    )
    @patch.object(chat_app, "_client")
    def test_missing_lex_configuration(self, mock_client):
        event = {
            "routeKey": "POST /chat",
            "body": json.dumps({
                "text": "Find foxes"
            })
        }

        response = chat_app.handler(event, None)

        self.assertEqual(response["statusCode"], 502)
        mock_client.assert_not_called()



if __name__ == "__main__":
    unittest.main()
