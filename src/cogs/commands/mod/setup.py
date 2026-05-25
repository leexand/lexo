import discord
from discord.ext import commands
import os
from src.cogs.events.captcha import generate_captcha, CodeButton

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='setup')
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, tipo: str = None):
        if not tipo:
            return await ctx.reply(embed=discord.Embed(
                description='❌ Debes especificar el tipo de setup.\n`l!setup verificacion`',
                color=0xff0000
            ))

        if tipo == 'verificacion':
            await self._setup_verificacion(ctx)

    async def _setup_verificacion(self, ctx):
        channel = self.bot.get_channel(int(os.getenv('VERIFICATION_CHANNEL_ID')))
        if not channel:
            return await ctx.reply(embed=discord.Embed(
                description='❌ Canal de verificación no encontrado.',
                color=0xff0000
            ))

        # limpiar mensajes anteriores del canal
        await channel.purge(limit=10)

        embed = discord.Embed(
            title='✅ Verificación',
            description='Bienvenido/a al servidor.\nPresiona el botón para verificarte y acceder al servidor.',
            color=0xffffff
        )
        embed.set_footer(text='lexoStudio — Sistema de verificación')

        await channel.send(embed=embed, view=VerifyButton())

        # usar send en lugar de reply — el purge puede haber eliminado el mensaje
        # original del comando, haciendo que reply falle con "Unknown message"
        msg = await ctx.send(embed=discord.Embed(
            description='✅ Panel de verificación configurado.',
            color=0xffffff
        ))
        # auto-eliminar la confirmación después de 5 segundos
        await msg.delete(delay=5)

# ─── Botón de verificación ────────────────────────────────────────────────────
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # sin expiración

    @discord.ui.button(label='Verificarme', style=discord.ButtonStyle.primary, emoji='✅')
    async def verify(self, button: discord.ui.Button, interaction: discord.Interaction):
        code, image = generate_captcha()

        await interaction.response.send_message(
            content='Escribe el código que aparece en la imagen:',
            file=discord.File(image, filename='captcha.png'),
            view=CodeButton(code),
            ephemeral=True
        )

def setup(bot: commands.Bot):
    bot.add_cog(Setup(bot))