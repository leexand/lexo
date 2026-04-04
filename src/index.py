import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# ─── Inicialización del cliente ───────────────────────────────────────────────
intents = discord.Intents(
    guilds=True,
    members=True,
    messages=True,
    message_content=True,
    reactions=True,
    moderation=True,
)

bot = commands.Bot(
        command_prefix=commands.when_mentioned_or("l!"), 
        intents=intents,
        help_command=None # desactivar el help por defecto de discord.py
    )

# ─── Handlers ─────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'[READY] {bot.user} está en línea')
    print(f'[READY] Conectado a {len(bot.guilds)} servidor(es)')
    await bot.sync_commands()
    print('[READY] Slash commands sincronizados')

# ─── Errores globales ─────────────────────────────────────────────────────────
@bot.event
async def on_error(event, *args, **kwargs):
    print(f'[ERROR] Error en evento {event}')

# ─── Arranque ─────────────────────────────────────────────────────────────────
async def init():
    async with bot:
        from handlers.cogloader import load_cogs
        await load_cogs(bot)
        token = os.getenv('TOKEN')
        if token is None:
            raise RuntimeError('TOKEN environment variable is not set')
        await bot.start(token)

asyncio.run(init())