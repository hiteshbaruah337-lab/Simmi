import asyncio
import os
import time
import sys
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# =============== PORT WEB SERVER FOR RENDER ================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = "<h1>Spam Bot Running</h1>"
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

web_thread = Thread(target=run_web_server, daemon=True)
web_thread.start()

# =============== EVENT LOOP FIX ================
if sys.version_info[0] == 3 and sys.version_info[1] >= 10:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

# =============== CONFIG ================
API_ID = int(os.environ.get("API_ID", 38652766))
API_HASH = os.environ.get("API_HASH", "45e99bc7cbfab2584e7cd5b94fe538d8")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8931408596:AAH-7SkyKtohZqKPE8ixyEfCV04h_rXagc8")
OWNER_ID = int(os.environ.get("OWNER_ID", 8424396068))

app = Client("spam_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# =============== SPAM TRACKER ================
spam_active = {}
spam_count = {}

# =============== GET CLICKABLE MENTION ================
async def get_mention(client, user_input, message):
    if message.reply_to_message:
        target = message.reply_to_message.from_user
        return target.mention, target.first_name
    
    if user_input and user_input.startswith("@"):
        try:
            target = await client.get_users(user_input)
            return target.mention, target.first_name
        except:
            return user_input, None
    
    if user_input and user_input.isdigit():
        try:
            target = await client.get_users(int(user_input))
            return target.mention, target.first_name
        except:
            return f"`{user_input}`", None
    
    return None, None

# =============== SPAM LOOP ================
async def spam_loop(client, chat_id, target_mention, target_name, message_text, count):
    global spam_active, spam_count
    
    spam_active[chat_id] = True
    sent = 0
    
    final_msg = f"{target_mention} {message_text}"
    
    try:
        if count == -1:  # Unlimited
            await client.send_message(chat_id, f"UNLIMITED SPAM STARTED\nTarget: {target_mention}\nStop: .stopspam")
            
            while spam_active.get(chat_id, False):
                try:
                    await client.send_message(chat_id, final_msg)
                    sent += 1
                except:
                    pass
                await asyncio.sleep(0)
        else:  # Limited
            status = await client.send_message(chat_id, f"Spamming {count} messages...")
            
            for i in range(count):
                if not spam_active.get(chat_id, True):
                    break
                try:
                    await client.send_message(chat_id, final_msg)
                    sent += 1
                except:
                    pass
                await asyncio.sleep(0)
            
            await status.edit_text(f"SPAM COMPLETE!\nSent: {sent}/{count} messages")
    except:
        pass
    finally:
        spam_active[chat_id] = False
        spam_count[chat_id] = sent

# =============== SPAM COMMAND ================
@app.on_message(filters.command("spam", prefixes=".") & filters.group)
async def spam_command(client, message: Message):
    # Only owner
    if message.from_user.id != OWNER_ID:
        await message.reply_text(f"Only owner! ID: {OWNER_ID}")
        return
    
    chat_id = message.chat.id
    
    if spam_active.get(chat_id, False):
        await message.reply_text(f"Spam active! Use .stopspam")
        return
    
    parts = message.text.split(maxsplit=3)
    
    if len(parts) < 2 and not message.reply_to_message:
        await message.reply_text(
            "Usage:\n"
            ".spam @user message - Unlimited\n"
            ".spam @user 100 message - Limited\n"
            "Reply -> .spam 100 message\n"
            ".stopspam - Stop"
        )
        return
    
    # Get target
    target_mention = None
    target_name = None
    arg_index = 1
    
    if len(parts) >= 2 and (parts[1].startswith("@") or parts[1].isdigit()):
        target_mention, target_name = await get_mention(client, parts[1], message)
        arg_index = 2
    elif message.reply_to_message:
        target_mention, target_name = await get_mention(client, None, message)
        arg_index = 1
    else:
        await message.reply_text("Tag a user or reply!")
        return
    
    if not target_mention:
        await message.reply_text("Invalid user!")
        return
    
    # Get count and message
    count = -1
    spam_msg = ""
    
    if len(parts) > arg_index:
        try:
            count = int(parts[arg_index])
            if len(parts) > arg_index + 1:
                spam_msg = parts[arg_index + 1]
            else:
                await message.reply_text("Message likho!")
                return
        except ValueError:
            spam_msg = parts[arg_index]
            count = -1
    
    if not spam_msg:
        await message.reply_text("Message likho!")
        return
    
    if str(count).lower() in ["unlimited", "0"]:
        count = -1
    
    try:
        await message.delete()
    except:
        pass
    
    asyncio.create_task(spam_loop(client, chat_id, target_mention, target_name, spam_msg, count))

# =============== STOP SPAM ================
@app.on_message(filters.command("stopspam", prefixes="."))
async def stop_spam(client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("Only owner!")
        return
    
    chat_id = message.chat.id
    
    if not spam_active.get(chat_id, False):
        await message.reply_text("No active spam!")
        return
    
    spam_active[chat_id] = False
    total = spam_count.get(chat_id, 0)
    
    try:
        await message.delete()
    except:
        pass
    
    await client.send_message(chat_id, f"SPAM STOPPED!\nSent: {total} messages")

# =============== START ================
@app.on_message(filters.command("start", prefixes="."))
async def start_command(client, message: Message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text(f"Only owner! ID: {OWNER_ID}")
        return
    
    await message.reply_text(
        "SPAM BOT\n\n"
        "Commands:\n"
        ".spam @user message - Unlimited\n"
        ".spam @user 100 message - Limited\n"
        ".stopspam - Stop spam\n\n"
        "Features:\n"
        "- Clickable mention\n"
        "- Ultra fast speed\n"
        "- Only owner can use"
    )

# =============== MAIN ================
if __name__ == "__main__":
    print("=" * 40)
    print("SPAM BOT STARTED")
    print(f"Owner: {OWNER_ID}")
    print("Commands: .spam | .stopspam")
    print("=" * 40)
    
    app.run()
