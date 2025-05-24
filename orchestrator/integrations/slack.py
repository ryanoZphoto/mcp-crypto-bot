import os
import requests
from typing import Optional

# Load environment variables
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")  # For more advanced features
SLACK_CHANNEL = "#general"  # Default channel


def send_slack_message(text: str, channel: Optional[str] = None) -> bool:
    """
    Send a message to a Slack channel using the configured webhook URL.

    Args:
        text (str): The message to send.
        channel (Optional[str]): Slack channel (not used with webhook,
                                 reserved for future bot token usage).

    Returns:
        bool: True if sent successfully, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        print(
            f"Warning: SLACK_WEBHOOK_URL is not set. Slack message not "
            f"sent: {text}"
        )
        return False

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL, json={"text": text}, timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Slack message failed: {e}")
        return False


# Example of a more advanced Slack integration (optional)
# Requires slack_sdk (pip install slack_sdk)
# from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError

# def send_slack_message_advanced(message: str, channel: str = SLACK_CHANNEL):
#     if not SLACK_BOT_TOKEN:
#         print(
#             "Warning: SLACK_BOT_TOKEN not set. Cannot send advanced message."
#         )
#         return False
#
#     client = WebClient(token=SLACK_BOT_TOKEN)
#     try:
#         response = client.chat_postMessage(channel=channel, text=message)
#         return response["ok"]
#     except SlackApiError as e:
#         print(f"Error sending advanced Slack message: {e.response['error']}")
#         return False


if __name__ == '__main__':
    # Test the Slack integration
    if send_slack_message(
        "Hello from the Trading Bot! This is a test message."
    ):
        print("Test message sent successfully to Slack.")
    else:
        print("Failed to send test message to Slack.")
