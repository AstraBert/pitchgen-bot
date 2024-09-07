from discord import Client, Intents
import time
from dotenv import load_dotenv
import os
from utils import ChatAnthropic, SessionHistory, chat_completion, ImageGen, read_config, Summarizer

load_dotenv()

CHANNEL_ID = int(os.getenv("channel_id"))
TOKEN = os.getenv("discord_bot")
ANTRHOPIC_API_KEY = os.getenv("anthropic_api_key")
OPENAI_API_KEY = os.getenv("openai_api_key")
SUPABASE_API_KEY = os.getenv("supabase_api_key")
SUPABASE_URL = os.getenv("supabase_url")
sess_hist = SessionHistory(SUPABASE_API_KEY, SUPABASE_URL)
SESSION_ID = sess_hist.generate_session_id()
config_opts = read_config()
N_IMGS = config_opts["num_images"]
LIMIT_HISTORY = config_opts["limit_history"]
image_generator = ImageGen(OPENAI_API_KEY, N_IMGS)
summarizer = Summarizer(OPENAI_API_KEY)


intents = Intents.default()
intents.messages = True

bot = Client(intents=intents)

@bot.event
async def on_ready():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Print a confirmation
        print(f"Connected to the channel: {channel.name} ({channel.id})")

        # Send the welcome message
        await channel.send(
            f"The bot was activated at: {time.time()}"
        )
    else:
        print(
            "Unable to find the specified channel ID. Make sure the ID is correct and the bot has the necessary permissions."
        )

@bot.event
async def on_message(message):
    global SESSION_ID, N_IMGS, LIMIT_HISTORY, ANTRHOPIC_API_KEY, SUPABASE_API_KEY, SUPABASE_URL, image_generator, OPENAI_API_KEY
    if message.author == bot.user:
        return
    
    elif message.content: 
        if not message.content.startswith("!"):
            print(
                f"Got content {message.content} from {message.author}"
            )
            chatter = ChatAnthropic(ANTRHOPIC_API_KEY, SUPABASE_API_KEY, SUPABASE_URL, str(message.author).replace("\'","\'\'"), SESSION_ID, summarizer)
            to_send, imgs = chat_completion(chatter, image_generator, message.content, LIMIT_HISTORY)
            await message.channel.send(to_send)
            for url in imgs:
                await message.channel.send(f"![generated_image]({url})")
        else:
            if message.content.startswith("!newsession"):
                SESSION_ID = sess_hist.generate_session_id()
                await message.channel.send("Successfully updated session ID")
            elif message.content.startswith("!imagenum"):
                N_IMGS = int(message.content.split(" ")[1])
                image_generator = ImageGen(OPENAI_API_KEY, N_IMGS) 
                await message.channel.send("Successfully updated number of images to generate") 
            elif message.content.startswith("!limithist"):
                LIMIT_HISTORY = int(message.content.split(" ")[1])
                await message.channel.send("Successfully updated limit of message history retrieval") 
bot.run(TOKEN)