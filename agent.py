import os
import json
import requests

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
MEDIA_ID = os.getenv("MEDIA_ID")

BASE_URL = "https://graph.facebook.com/v19.0"


def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def get_comments():
    url = f"{BASE_URL}/{MEDIA_ID}/comments"

    params = {
        "access_token": ACCESS_TOKEN,
        "fields": "id,text,username,timestamp"
    }

    response = requests.get(url, params=params)
    return response.json()


def reply_to_comment(comment_id, reply_message):
    url = f"{BASE_URL}/{comment_id}/replies"

    payload = {
        "message": reply_message,
        "access_token": ACCESS_TOKEN
    }

    response = requests.post(url, data=payload)
    return response.json()


def get_recipient_id(username):
    mapping = load_json("recipient_mapping.json", {})
    return mapping.get(username)


def send_private_dm(recipient_id, dm_message):
    url = f"{BASE_URL}/me/messages"

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": dm_message
        },
        "messaging_type": "RESPONSE"
    }

    params = {
        "access_token": ACCESS_TOKEN
    }

    response = requests.post(url, json=payload, params=params)
    return response.json()


def main():
    if not ACCESS_TOKEN:
        print("❌ ACCESS_TOKEN missing in GitHub Secrets")
        return

    if not MEDIA_ID:
        print("❌ MEDIA_ID missing in GitHub Secrets")
        return

    rules = load_json("rules.json", {})
    processed_comments = load_json("processed_comments.json", [])

    comments_response = get_comments()
    print("Comments response:", comments_response)

    if "data" not in comments_response:
        print("❌ Could not fetch comments")
        return

    comments = comments_response["data"]

    for comment in comments:
        comment_id = comment.get("id")
        text = comment.get("text", "").strip().lower()
        username = comment.get("username", "")

        if not comment_id or comment_id in processed_comments:
            continue

        print(f"✅ New comment found from @{username}: {text}")

        if text in rules:
            rule = rules[text]

            public_reply = rule.get("public_reply", "Check your DM, details sent.")
            dm_message = rule.get("dm_message", "")

            reply_response = reply_to_comment(comment_id, public_reply)
            print("💬 Public reply response:", reply_response)

            recipient_id = get_recipient_id(username)

            if recipient_id:
                dm_response = send_private_dm(recipient_id, dm_message)
                print("📩 DM response:", dm_response)
            else:
                print(f"⚠️ DM not sent to @{username}.")
                print(f"⚠️ Intended DM message: {dm_message}")
                print("⚠️ No recipient ID found in recipient_mapping.json.")
                print("⚠️ User must message your Instagram business account first.")

        else:
            print(f"ℹ️ No rule matched for comment: {text}")

        processed_comments.append(comment_id)

    save_json("processed_comments.json", processed_comments)


if __name__ == "__main__":
    main()
