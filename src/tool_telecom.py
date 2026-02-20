import os
import threading
import asyncio
import json
import random
import time
import general as gen
import global_cfg as glb
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# flag of whether the Telegram bot is handling a message, when grok_handling is 1,
# it means the bot is handling a message and waiting for the reply from grok, at 
# this time, if the bot receives another message, it will reply with a non-favored 
# message to ask the user to wait until the current message is handled, and when 
# grok_handling is 0, it means the bot is not handling any message, at this time, 
# if the bot receives a message, it will handle the message and set grok_handling
# to 1 until it receives the reply from grok and send it back to the user, then set 
# grok_handling back to 0 to handle the next message
grok_handling = 0

# read Telegram bot configuration
cfg_telegram = gen.get_cfg("telegram")
# create a fast LUT from agent id to agent name for later use
agent_id_name_map = {}
for name in cfg_telegram:
    if name.startswith("agent"):
        agent_id = int(cfg_telegram[name]['id'])
        agent_id_name_map.update({agent_id: name})

non_favored_reply_table = [
    "Fuck you bro!",
    "Beat it!",
    "Get lost!",
    "Scram!",
    "Take a hike!",
    "Buzz off!",
    "Hit the road!",
    "Piss off!",
    "Get outta here!",
    "Back off!",
    "Shove off!",
    "Motherfucker!",
]

# split_message
# Cut pure text message to multiple segments suitable for Telegram (default limit 4096 characters).
def split_message(text: str, max_length: int = 4096) -> list[str]:
    if len(text) <= max_length:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        chunk = text[:max_length]
        split_pos = chunk.rfind('\n')
        if split_pos == -1 or split_pos < max_length // 2:
            space_pos = chunk.rfind(' ')
            if space_pos > max_length // 2:
                split_pos = space_pos
        if split_pos == -1 or split_pos < max_length // 2:
            split_pos = max_length
        chunks.append(text[:split_pos].rstrip())
        text = text[split_pos:].lstrip()
    return chunks


async def non_favored_access_reply(update: Update):
    if random.randint(0, 3) == 0:
        await update.message.reply_text(non_favored_reply_table[random.randint(0, len(non_favored_reply_table) - 1)])

def tackle_non_favored_access(update: Update):
    access_id = update.message.chat.id
    if access_id == cfg_telegram['group']['id']:
        return 1
    for i in cfg_telegram['user']:
        if cfg_telegram['user'][i] == access_id:
            return 2
    return 0

# start:
# a handler function when telegram bot receives a /start message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text("start")

# help_command:
# a handler function when telegram bot receives a /help message
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text("help")

# message_handler:
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global grok_handling
    while True:
        if not grok_handling:
            if update:
                print(f"Received Telegram message: {update.message.text} from {update.message.chat.id}")
                # handle the message and send reply if needed
                with open(glb.grok_fcomm_in_tele, 'w') as f:
                    f.write(update.message.text)
                    f.write(glb.grok_fcomm_start)
                grok_handling = 1
            else:
                await asyncio.sleep(0.1)
        else:
            if os.path.isfile(glb.grok_fcomm_out_tele):
                with open(glb.grok_fcomm_out_tele, 'r') as f:
                    fcomm_rx = f.read()
                done = 0
                end = 0
                if fcomm_rx.find(glb.grok_fcomm_done) >= 0:
                    fcomm_rx = fcomm_rx.replace(glb.grok_fcomm_done, '')
                    done = 1
                    with open(glb.grok_fcomm_out_tele, 'w') as f:
                        f.write("")
                elif fcomm_rx.find(glb.grok_fcomm_end) >= 0:
                    fcomm_rx = fcomm_rx.replace(glb.grok_fcomm_end, '')
                    end = 1
                    with open(glb.grok_fcomm_out_tele, 'w') as f:
                        f.write("")
                if done or end:
                    # not empty message, send it back to user
                    fcomm_rx = fcomm_rx.strip()
                    if fcomm_rx:
                        parts = split_message(fcomm_rx)
                        for part in parts:
                            await update.message.reply_text(part)
                    if end:
                        grok_handling = 0
                        return
            else:
                await asyncio.sleep(0.1)

# echo:
# a handler function when telegram bot receives a normal message (not command), 
# it will reply with the same message content,
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    agent = agent_id_name_map.get(int(context.bot.id))
    if agent:
        if agent == 'agent00':
            if not grok_handling:
                await update.message.reply_text("Whassup boss?")
                await message_handler(update, context)
            else:
                await update.message.reply_text("Hold on, I'm handling something for you.")
        else:
            pass

# bot_daemon:
# this function runs the Telegram bot in a separate thread to avoid blocking the main thread 
# of the agent, and uses asyncio to run the bot asynchronously, so that it can handle multiple
# messages at the same time without blocking each other, the bot will also check the access 
# of the incoming messages and reply with a non-favored message if the access is not allowed,
# and only allow messages from the specified user ids or group id in the configuration file 
# to interact with the bot, you can modify the access control logic in the tackle_non_favored_access
# function as needed, for example, you can add more user ids or group ids to allow, or you can
# implement a more complex access control logic based on your requirements.
def bot_daemon(token: str, bot_name: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async def _start_bot(token=token):
        app = Application.builder().token(token).build()
        # add handlers for start, help and echo commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        # start the bot
        await app.initialize()
        await app.updater.start_polling(drop_pending_updates=True)
        await app.start()
        print(f"Agent {bot_name} Start...")
        await asyncio.Event().wait()
    try:
        loop.run_until_complete(_start_bot(token))
    except Exception as e:
        print(f"Agent {bot_name} Error: {e}")


# start_telegram_bot:
# starts every bots defined in the telegram configuration file in a separate thread,
# called by main.py at the beginning to start the Telegram bot
def start_telegram_bot():
    # starts every bots defined in the telegram configuration file in a separate thread, 
    # and also starts a daemon thread to handle the messages received from Telegram
    for name in cfg_telegram:
        if name.startswith("agent"):
            token = cfg_telegram[name]['token']
            bot_thread = threading.Thread(target=bot_daemon, args=(token, name), daemon=True)
            bot_thread.start()

