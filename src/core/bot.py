import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.core.cogloader import load_cogs

load_dotenv()

# ─── Intents ────────────────────────────────────────────────────────────────
intents = discord.Intents(
    guilds=True,
    members=True,
    messages=True,
    message_content=True,
    reactions=True,
    moderation=True,
)

# ─── Cliente ────────────────────────────────────────────────────────────────
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("l!"),
    intents=intents,
    help_command=None
)

# ─── Eventos ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'[READY] {bot.user} está en línea')
    print(f'[READY] Conectado a {len(bot.guilds)} servidor(es)')
    
    await bot.sync_commands()
    
    print('[READY] Slash commands sincronizados')

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'[ERROR] Error en evento {event}')

# ─── Arranque ───────────────────────────────────────────────────────────────
async def start_bot():
    async with bot:
        await load_cogs(bot)

        token = os.getenv('TOKEN')

        if token is None:
            raise RuntimeError('TOKEN environment variable is not set')

        await bot.start(token)