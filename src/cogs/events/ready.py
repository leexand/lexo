import discord
from discord.ext import commands
from datetime import datetime, timezone
import os
import asyncio

class Ready(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_startup())

    async def on_startup(self):
        await self.bot.wait_until_ready() # esperar a que el bot esté listo
        await self.bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name='a InterWorld formarse'
        )
)

        channel = self.bot.get_channel(int(os.getenv('START_CHANNEL_ID')))
        if not channel:
            return

        # limpiar mensaje de inicio anterior
        async for msg in channel.history(limit=1):
            await msg.delete()

        dev = await self.bot.fetch_user(int(os.getenv('DEV')))

        embed = discord.Embed(
            title=f'🟩 Inicio de {self.bot.user.name}',
            color=0xffffff,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name='Estado', value='Activo', inline=True)
        embed.add_field(name='Servidores', value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name='Versión', value=f'Pycord {discord.__version__}', inline=True)
        embed.set_footer(text=f'Creado por {dev.name}')

        await channel.send(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Ready(bot))