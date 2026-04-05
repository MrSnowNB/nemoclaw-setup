#!/usr/bin/env python3
"""
Telegram CLI Bridge
Send messages to Telegram and receive them back to this chat.
"""
import os
import sys
import asyncio
import argparse
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.getenv("TELEGRAM_MY_CHAT_ID")  # Your personal chat ID

def forward_to_alice(message: str):
    """Forward a Telegram message back to Mark via this chat"""
    print(f"\n📨 ALICE-INCOMING: {message}")
    print("=" * 60)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Alice is listening. Send me messages and I'll echo them back to Mark!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        text = update.message.text
        forward_to_alice(text)

async def send_message(args):
    """Send a message to Telegram via CLI"""
    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not set")
        return
    
    if not MY_CHAT_ID:
        print("❌ Error: TELEGRAM_MY_CHAT_ID not set")
        return

    message = " ".join(args)
    
    try:
        import httpx
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={
                "chat_id": MY_CHAT_ID,
                "text": message
            })
        
        if resp.status_code == 200:
            print(f"\n✅ Sent to Telegram: {message}")
        else:
            print(f"\n❌ Failed to send: {resp.status_code}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Telegram CLI Bridge")
    parser.add_argument("--send", nargs="+", help="Send a message to Telegram")
    parser.add_argument("--listen", action="store_true", help="Start listening for incoming messages")
    parser.add_argument("--test", action="store_true", help="Test connection to Telegram")

    args = parser.parse_args()

    if args.test:
        print("🔍 Testing Telegram connection...")
        if not BOT_TOKEN:
            print("❌ Set TELEGRAM_BOT_TOKEN env var")
            return
        print("✅ Token configured")
        if not MY_CHAT_ID:
            print("❌ Set TELEGRAM_MY_CHAT_ID env var")
        else:
            print(f"✅ Target: {MY_CHAT_ID}")
        return

    if args.send:
        await send_message(args.send)
        return

    if args.listen or not args.send:
        print("🤖 Starting Telegram listener...")
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        await app.start()
        print("👂 Listening for messages. Press Ctrl+C to stop.\n")
        await app.updater.start_polling()
        await app.run_until_stopped()

if __name__ == "__main__":
    asyncio.run(main())
