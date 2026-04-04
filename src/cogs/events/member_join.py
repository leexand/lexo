import discord
from discord.ext import commands
import os

class MemberJoin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            # asignar rol Sin verificar
            role = member.guild.get_role(int(os.getenv('UNVERIFIED_ROLE_ID')))
            if role:
                await member.add_roles(role)

        except Exception as e:
            print(f'[MemberJoin] Error: {e}')

def setup(bot: commands.Bot):
    bot.add_cog(MemberJoin(bot))    