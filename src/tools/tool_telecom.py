import os
import threading
import asyncio
import json
import random
import time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import global_cfg as glb
import general as gen


# tool_telecom costs approximately 150 tokens when sent to the LLM vendor.
tool_define_telecom = {
    "type": "function",
    "function": {
        "name": "telecom",
        "description": (
            "Send a Telegram message to the user or to a group chat. "
            "Use this tool to notify the user of task completion, errors, or important information. "
            "Messages are sent asynchronously and do not block execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Use exactly ONE of the following commands with the syntax shown:\n\n"
                    "<target> <message>\n"
                    "target: 'user' for direct message, 'group' for group chat.\n"
                    "message: The message content to send. Use plain text, no HTML or markdown."
                }
            },
            "required": ["command"]
        }
    }
}

tool_brief_telecom = """Send Telegram messages to the user or group chat. """

tool_rule_telecom = """Messages can only send to default users or groups. """

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

tool_telecom_send_target = 'user'  # or 'group', decide whether to send message to user or group, if user, the bot will reply to the user who sent the message, if group, the bot will send message to the group defined in the configuration file
last_chat_user = cfg_telegram['user']['valid_id_1']  # the chat id of the last user who sent a message, used to reply to the user when tool_telecom_send_target is 'user'
last_chat_group = cfg_telegram['group']['id_1']  # the chat id of the last message received, used to reply to the user when tool_telecom_send_target is 'user'

non_favored_reply_table = [
    "Fuck you!", "Beat it!", "Get lost!", "Scram!", "Take a hike!",
    "Buzz off!", "Hit the road!", "Piss off!", "Get outta here!",
    "Back off!", "Shove off!", "Motherfucker!",
]

# split_message:
# Cut pure text message to multiple segments suitable for Telegram (default limit 4096 characters).
# no longer used, replace by text_to_file
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

# general_telegram_send:
# a general function to send message to Telegram
async def general_telegram_send(handler, fcomm_tx):
    fcomm_tx = fcomm_tx.strip()
    if fcomm_tx:
        remote_tx = gen.xml_parser(fcomm_tx, "grok_tele_file")
    else:
        return
    # reply to the user's message
    if isinstance(handler, Update):
        for seq in remote_tx:
            if seq.__contains__("content"):
                await handler.message.reply_text(seq["content"]["#text"])
            else:
                for key in seq["pars"]["#list"]:
                    if key.find("name=") == 0:
                        file_name = key[5:].strip("\"")
                reply_file = f"{glb.workspace}{glb.path_sep}fcomm{glb.path_sep}{file_name}"
                content = seq["file_content"]["#text"]
                with open(reply_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                brief = content[:content.find(' ', 100)] + "..." if len(content) > 100 else content
                await handler.message.reply_document(document=open(reply_file, 'rb'),
                                                    filename=file_name,
                                                    caption=brief)
    # send message to the user or group
    # bug fixed: ContextTypes.DEFAULT_TYPE is not allowed to compare instance type
    else:
        if tool_telecom_send_target == 'user':
            id = last_chat_user
        else:
            id = last_chat_group
        for seq in remote_tx:
            if seq.__contains__("content"):
                await handler.bot.send_message(chat_id=id, text=seq["content"]["#text"])
            else:
                for key in seq["pars"]["#list"]:
                    if key.find("name=") == 0:
                        file_name = key[5:].strip("\"")
                reply_file = f"{glb.workspace}{glb.path_sep}fcomm{glb.path_sep}{file_name}"
                content = seq["file_content"]["#text"]
                with open(reply_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                brief = content[:content.find(' ', 100)] + "..." if len(content) > 100 else content
                await handler.bot.send_document(chat_id=id, 
                                                document=open(reply_file, 'rb'), 
                                                filename=file_name, 
                                                caption=brief) 
            

anti_flood_cnt = 0
async def non_favored_access_reply(update: Update):
    print(f"Non-favored access attempt detected from chat id: {update.message.chat.id}")
    global anti_flood_cnt
    if anti_flood_cnt > 0:
        if random.randint(0, 3) == 0:
            await update.message.reply_text(non_favored_reply_table[random.randint(0, len(non_favored_reply_table) - 1)])
            anti_flood_cnt -= 1

def tackle_non_favored_access(update: Update):
    access_id = update.message.chat.id
    for i in cfg_telegram['group']:
        if cfg_telegram['group'][i] == access_id:
            return 1
    for i in cfg_telegram['user']:
        if cfg_telegram['user'][i] == access_id:
            return 2
    return 0

# start:
# a handler function when telegram bot receives a /start message
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text("Start: Hello! I'm Grok, your AI assistant. How can I /help you today?")

# help_command:
# a handler function when telegram bot receives a /help message
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    reply = f"Help: Here are the commands you can use:\n{gen.command_description}"
    await update.message.reply_text(reply)

# reset_command:
# a handler function when telegram bot receives a /r message, it will reset the conversation
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['r']())

# quit_command:
# a handler function when telegram bot receives a /q message, it will quit the bot
async def quit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text("Goodbye!")
    gen.command_handler['q']()


# memory_save_command:
# a handler function when telegram bot receives a /memory message, it will print the current conversation memory
async def memory_save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['ms']())

# memory_clear_command:
# a handler function when telegram bot receives a /cm message, it will clear the conversation memory
async def memory_clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['mc']())

# confirm_enable_command:
# a handler function when telegram bot receives a /ce message, it will enable the confirm mode
async def confirm_enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['ce']())

# confirm_disable_command:
# a handler function when telegram bot receives a /cd message, it will disable the confirm mode
async def confirm_disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['cd']())

# tool_enable_command:
# a handler function when telegram bot receives a /te message, it will enable the tool use
async def tool_enable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['te']())

# tool_disable_command:
# a handler function when telegram bot receives a /td message, it will disable the tool use
async def tool_disable_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if tackle_non_favored_access(update) == 0:
        await non_favored_access_reply(update)
        return
    await update.message.reply_text(gen.command_handler['td']())

# message_handler:
# a handler function when telegram bot receives a normal message (not command),
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global grok_handling
    while True:
        if not grok_handling:
            if update:
                print(f"Received Telegram message: {update.message.text} from {update.message.chat.id}")
                # handle the message and send reply if needed
                with open(glb.grok_fcomm_in_tele, 'w') as f:
                    f.write(update.message.text)
                    f.write('\n' + glb.grok_fcomm_start)
                grok_handling = 1
            else:
                await asyncio.sleep(1)
        else:
            if os.path.isfile(glb.grok_fcomm_out_tele):
                with open(glb.grok_fcomm_out_tele, 'r') as f:
                    fcomm_tx = f.read()
                done = 0
                end = 0
                if fcomm_tx.find(glb.grok_fcomm_done) >= 0:
                    fcomm_tx = fcomm_tx.replace(glb.grok_fcomm_done, '')
                    done = 1
                    with open(glb.grok_fcomm_out_tele, 'w') as f:
                        f.write("")
                if fcomm_tx.find(glb.grok_fcomm_end) >= 0:
                    fcomm_tx = fcomm_tx.replace(glb.grok_fcomm_end, '')
                    end = 1
                    with open(glb.grok_fcomm_out_tele, 'w') as f:
                        f.write("")
                if done or end:
                    # not empty message, send it back to user
                    await general_telegram_send(update, fcomm_tx)
                    if end:
                        grok_handling = 0
                        return
            else:
                await asyncio.sleep(1)

# echo:
# a handler function when telegram bot receives a normal message (not command), 
# it will reply with the same message content,
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if tackle_non_favored_access(update) == 0:
            await non_favored_access_reply(update)
            return
        global last_chat_user, last_chat_group
        id = update.message.chat.id
        if id > 0:
            last_chat_user = id
        else:
            last_chat_group = id
        agent = agent_id_name_map.get(int(context.bot.id))
        if agent:
            if agent == 'agent00':
                if not grok_handling:
                    placeholder = await update.message.reply_text("Whassup boss?")
                    await message_handler(update, context)
                    await placeholder.delete()
                else:
                    await update.message.reply_text("Hold on, I'm handling something for you.")
            else:
                pass
    except Exception as e:
        print(f"Error in echo handler: {e}")
        gen.reset_flag.append(f'Telegram Bot Error {e}')


# bot_daemon_send_message:
# this function is called by the main loop of the agent to send the message in grok
async def bot_daemon_send_message(context: ContextTypes.DEFAULT_TYPE):
    try:
        fcomm_tx = ""
        check_list = [glb.grok_fcomm_out_tele, glb.grok_fcomm_out_tele_active]
        for fcomm_file in check_list:
            if not os.path.isfile(fcomm_file):
                continue
            if grok_handling == 1 and fcomm_file == glb.grok_fcomm_out_tele:
                continue
            done = 0
            end = 0
            with open(fcomm_file, 'r') as f:
                fcomm_tx = f.read()
                if fcomm_tx.find(glb.grok_fcomm_done) >= 0:
                    with open(fcomm_file, 'w') as f:
                        f.write("")
                    fcomm_tx = fcomm_tx.replace(glb.grok_fcomm_done, '')
                    done = 1
                if fcomm_tx.find(glb.grok_fcomm_end) >= 0:
                    with open(fcomm_file, 'w') as f:
                        f.write("")
                    fcomm_tx = fcomm_tx.replace(glb.grok_fcomm_end, '')
                    end = 1
                fcomm_tx = fcomm_tx.strip()
            if fcomm_tx and (done or end):
                await general_telegram_send(context, fcomm_tx)
        global anti_flood_cnt
        if anti_flood_cnt < 3:
            anti_flood_cnt += 1
    except Exception as e:
        print(f"Error in bot_daemon_send_message: {e}")
        gen.reset_flag.append(f'Telegram Bot Error {e}')


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
        token = token.strip()
        app = Application.builder().token(token).build()
        # add handlers for start, help and echo commands
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("q", quit_command))
        app.add_handler(CommandHandler("r", reset_command))
        app.add_handler(CommandHandler("ms", memory_save_command))
        app.add_handler(CommandHandler("mc", memory_clear_command))
        app.add_handler(CommandHandler("ce", confirm_enable_command))
        app.add_handler(CommandHandler("cd", confirm_disable_command))
        app.add_handler(CommandHandler("te", tool_enable_command))
        app.add_handler(CommandHandler("td", tool_disable_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        # a periodic task to check the message from grok and send it to Telegram if needed, runs every 1 second
        app.job_queue.run_repeating(bot_daemon_send_message, interval=1)
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
        gen.reset_flag.append(f'Telegram Bot Error {e}')


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


# ================================================================
# Agent tool calls
# ================================================================
# tool_handle_telecom:
# an active tool for agent to send message to the last contacted user or the group
def tool_handle_telecom(agent_cmd):
    agent_cmd = agent_cmd.strip().split(' ', 1)
    if len(agent_cmd) < 2:
        return "Invalid command format for tool_telecom_send, must be '<target> <message>'"
    target = agent_cmd[0]
    message = agent_cmd[1]
    target = target.strip().lower()
    if target != 'user' and target != 'group':
        return "Invalid target for tool_telecom_send, must be 'user' or 'group'"
    global tool_telecom_send_target
    tool_telecom_send_target = target
    with open(glb.grok_fcomm_out_tele_active, 'w') as f:
        f.write(message)
        f.write('\n' + glb.grok_fcomm_end)
    return "Telecom tool: Successfully sent the message."

def tool_register():
    start_telegram_bot()
    return {
        "name": "telecom",
        "description": "Telecom tool for sending messages to users or groups.",
        "handler": tool_handle_telecom,
        "definition": tool_define_telecom,
        "prompt": {
            "brief": tool_brief_telecom,
            "rule": tool_rule_telecom
        }
    }
