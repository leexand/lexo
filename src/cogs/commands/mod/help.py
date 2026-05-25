import discord
from discord.ext import commands
from datetime import datetime, timezone


async def respond(ctx, **kwargs):
    """
    Helper universal para responder tanto en prefix como en slash commands.
    - ApplicationContext (slash) → ctx.respond()
    - Context (prefix)          → ctx.reply()
    """
    if isinstance(ctx, discord.ApplicationContext):
        await ctx.respond(**kwargs)
    else:
        await ctx.reply(**kwargs)


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_prefix(self, ctx):
        await self._help(ctx)

    @discord.slash_command(name='help', description='Ver todos los comandos de Lexo')
    async def help_slash(self, ctx):
        await self._help(ctx)

    async def _help(self, ctx):
        embed = discord.Embed(
            title='📖 Comandos de Lexo',
            color=0xffffff,
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(
            name='🔨 Moderación',
            value=(
                '`ban @user [razón]` — Banear usuario\n'
                '`unban <ID> [razón]` — Desbanear por ID\n'
                '`kick @user [razón]` — Expulsar usuario\n'
                '`mute @user [duración] [razón]` — Silenciar (10m, 1h, 1d)\n'
                '`unmute @user` — Quitar silencio\n'
                '`warn @user [razón]` — Advertir usuario\n'
                '`purge <1-100>` — Eliminar mensajes en masa\n'
                '`slowmode <segundos>` — Configurar slowmode\n'
                '`lockdown [razón]` — Bloquear canal\n'
                '`unlock` — Desbloquear canal'
            ),
            inline=False
        )

        embed.add_field(
            name='👤 Información',
            value=(
                '`userinfo [@user]` — Ver info de un usuario\n'
            ),
            inline=False
        )

        embed.add_field(
            name='⚙️ Configuración (admin)',
            value=(
                '`setup verificacion` — Desplegar panel de verificación\n'
            ),
            inline=False
        )

        embed.add_field(
            name='🤖 Automod (automático)',
            value=(
                '• Detección de spam\n'
                '• Bloqueo de links no permitidos\n'
                '• Filtro de menciones masivas\n'
                '• Detección de raids\n'
                '• Logs de edición y eliminación de mensajes'
            ),
            inline=False
        )

        embed.set_footer(text='Prefix: l! | También disponible como slash commands (/)')
        await respond(ctx, embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Help(bot))