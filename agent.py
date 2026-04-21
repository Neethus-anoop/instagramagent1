import os
import json
import re
import requests

# ----------------- CONFIGURATION -----------------
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

INPUT_POST_URL = os.getenv("INPUT_POST_URL", "").strip()
INPUT_KEYWORD = os.getenv("INPUT_KEYWORD", "").strip()
INPUT_REPLY = os.getenv("INPUT_REPLY", "").strip()

API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

RULES_FILE = "rules.json"
PROCESSED_FILE = "processed_comments.json"

# ----------------- HELPER FUNCTIONS -----------------
def load_json(filepath, default_value):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_value
    return default_value

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def extract_shortcode(url):
    match = re.search(r'instagram\.com/(?:p|reel)/([^/?#&]+)', url)
    return match.group(1) if match else None

# ----------------- MAIN LOGIC -----------------
def main():
    print("🤖 Starting Instagram Auto-Reply Bot...")

    if not ACCESS_TOKEN or not IG_USER_ID:
        print("❌ Error: ACCESS_TOKEN and IG_USER_ID must be set in environment variables.")
        return

    # Load State
    rules = load_json(RULES_FILE, {})
    processed_comments = load_json(PROCESSED_FILE,[])

    # 1. Check if we need to add a new rule from workflow dispatch inputs
    if INPUT_POST_URL and INPUT_KEYWORD and INPUT_REPLY:
        shortcode = extract_shortcode(INPUT_POST_URL)
        if shortcode:
            rules[shortcode] = {
                "keyword": INPUT_KEYWORD,
                "reply": INPUT_REPLY
            }
            print(f"✅ Added/Updated rule for shortcode '{shortcode}': Reply to '{INPUT_KEYWORD}'")
        else:
            print(f"⚠️ Could not extract shortcode from URL: {INPUT_POST_URL}")

    if not rules:
        print("ℹ️ No rules configured. Exiting.")
        save_json(RULES_FILE, rules)
        save_json(PROCESSED_FILE, processed_comments)
        return

    # 2. Fetch recent media items and their shortcodes
    print(f"📡 Fetching up to 50 recent media items for user {IG_USER_ID}...")
    media_url = f"{BASE_URL}/{IG_USER_ID}/media?fields=id,shortcode&limit=50&access_token={ACCESS_TOKEN}"
    media_response = requests.get(media_url).json()

    if "error" in media_response:
        print(f"❌ Error fetching media: {media_response['error'].get('message')}")
        return

    media_items = media_response.get("data",[])
    print(f"✅ Found {len(media_items)} media items.")

    # 3. Process each media item that matches a rule
    for media in media_items:
        shortcode = media.get("shortcode")
        media_id = media.get("id")

        if shortcode in rules:
            rule_keyword = rules[shortcode]["keyword"].lower()
            rule_reply = rules[shortcode]["reply"]
            
            print(f"🔍 Checking comments for media {shortcode} (ID: {media_id})...")
            comments_url = f"{BASE_URL}/{media_id}/comments?fields=id,text&limit=50&access_token={ACCESS_TOKEN}"
            comments_response = requests.get(comments_url).json()
            
            if "error" in comments_response:
                print(f"⚠️ Error fetching comments for {shortcode}: {comments_response['error'].get('message')}")
                continue
                
            comments = comments_response.get("data",[])
            
            # 4. Filter comments and reply
            for comment in comments:
                comment_id = comment.get("id")
                comment_text = comment.get("text", "")

                if comment_id in processed_comments:
                    continue  # Already replied
                
                if rule_keyword in comment_text.lower():
                    print(f"🎯 Trigger word '{rule_keyword}' found in comment ID: {comment_id}")
                    
                    # Post the reply
                    reply_url = f"{BASE_URL}/{comment_id}/replies"
                    payload = {
                        "message": rule_reply,
                        "access_token": ACCESS_TOKEN
                    }
                    reply_response = requests.post(reply_url, data=payload).json()
                    
                    if "id" in reply_response:
                        print(f"✅ Successfully replied to comment {comment_id}!")
                        processed_comments.append(comment_id)
                    else:
                        print(f"❌ Failed to reply to {comment_id}: {reply_response.get('error', {}).get('message')}")

    # 5. Save updated state back to disk
    save_json(RULES_FILE, rules)
    save_json(PROCESSED_FILE, processed_comments)
    print("💾 Saved state to disk. Bot run complete! 🎉")

if __name__ == "__main__":
    main()
