import os
import json
import re
import requests

# ---------------- CONFIGURATION ----------------
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

INPUT_POST_URL = os.getenv("INPUT_POST_URL", "").strip()
INPUT_KEYWORD = os.getenv("INPUT_KEYWORD", "").strip()
INPUT_PUBLIC_REPLY = os.getenv("INPUT_PUBLIC_REPLY", "").strip()
INPUT_DM_MESSAGE = os.getenv("INPUT_DM_MESSAGE", "").strip()

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

RULES_FILE = "rules.json"
PROCESSED_FILE = "processed_comments.json"


# ---------------- HELPER FUNCTIONS ----------------
def load_json(filepath, default_value):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_value
    return default_value


def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def extract_shortcode(url):
    match = re.search(r"instagram\.com/(?:p|reel)/([^/?#]+)/?", url)
    return match.group(1) if match else None


def send_public_reply(comment_id, message):
    reply_url = f"{BASE_URL}/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": ACCESS_TOKEN
    }
    response = requests.post(reply_url, data=payload).json()
    return response


def send_private_dm_unsupported(username, dm_message):
    """
    Placeholder:
    Your current bot can reply publicly.
    Sending Instagram DM requires extra API support/permissions and a different flow.
    """
    print(f"⚠️ DM not sent to @{username}.")
    print(f"⚠️ Intended DM message: {dm_message}")
    print("⚠️ Private DM requires Instagram Messaging API setup, permissions, and recipient mapping.")


# ---------------- MAIN LOGIC ----------------
def main():
    print("🚀 Starting Instagram Auto-Reply Bot...")

    if not ACCESS_TOKEN or not IG_USER_ID:
        print("❌ Error: ACCESS_TOKEN and IG_USER_ID must be set in environment variables.")
        return

    # Load state
    rules = load_json(RULES_FILE, {})
    processed_comments = load_json(PROCESSED_FILE, [])

    # 1. Add/update a rule from workflow inputs
    if INPUT_POST_URL and INPUT_KEYWORD and INPUT_PUBLIC_REPLY and INPUT_DM_MESSAGE:
        shortcode = extract_shortcode(INPUT_POST_URL)
        if shortcode:
            rules[shortcode] = {
                "keyword": INPUT_KEYWORD,
                "public_reply": INPUT_PUBLIC_REPLY,
                "dm_message": INPUT_DM_MESSAGE
            }
            print(f"✅ Added/Updated rule for shortcode '{shortcode}'")
        else:
            print(f"⚠️ Could not extract shortcode from URL: {INPUT_POST_URL}")

    if not rules:
        print("ℹ️ No rules configured. Exiting.")
        save_json(RULES_FILE, rules)
        save_json(PROCESSED_FILE, processed_comments)
        return

    # 2. Fetch recent media
    print(f"📥 Fetching up to 50 recent media items for user {IG_USER_ID}...")
    media_url = f"{BASE_URL}/{IG_USER_ID}/media?fields=id,shortcode&limit=50&access_token={ACCESS_TOKEN}"
    media_response = requests.get(media_url).json()

    if "error" in media_response:
        print(f"❌ Error fetching media: {media_response['error'].get('message')}")
        return

    media_items = media_response.get("data", [])
    print(f"✅ Found {len(media_items)} media items.")

    # 3. Check comments for posts that have rules
    for media in media_items:
        media_id = media.get("id")
        shortcode = media.get("shortcode")

        if shortcode not in rules:
            continue

        rule_keyword = rules[shortcode]["keyword"].lower()
        public_reply = rules[shortcode]["public_reply"]
        dm_message = rules[shortcode]["dm_message"]

        print(f"🔎 Checking comments for media shortcode {shortcode} (ID: {media_id})...")

        comments_url = f"{BASE_URL}/{media_id}/comments?fields=id,text,username&limit=50&access_token={ACCESS_TOKEN}"
        comments_response = requests.get(comments_url).json()

        if "error" in comments_response:
            print(f"❌ Error fetching comments for {shortcode}: {comments_response['error'].get('message')}")
            continue

        comments = comments_response.get("data", [])

        # 4. Filter comments and reply
        for comment in comments:
            comment_id = comment.get("id")
            comment_text = comment.get("text", "")
            username = comment.get("username", "unknown_user")

            if comment_id in processed_comments:
                continue

            if rule_keyword in comment_text.lower():
                print(f"💬 Trigger word '{rule_keyword}' found in comment ID: {comment_id}")

                # Send public reply
                public_response = send_public_reply(comment_id, public_reply)

                if "id" in public_response:
                    print(f"✅ Public reply sent to comment {comment_id}")
                else:
                    print(f"❌ Failed to send public reply: {public_response}")

                # Try private DM
                send_private_dm_unsupported(username, dm_message)

                # Mark as processed
                processed_comments.append(comment_id)

    # 5. Save state
    save_json(RULES_FILE, rules)
    save_json(PROCESSED_FILE, processed_comments)
    print("✅ Saved state to disk. Bot run complete.")


if __name__ == "__main__":
    main()
