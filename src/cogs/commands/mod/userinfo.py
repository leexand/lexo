import discord
from discord.ext import commands
from datetime import datetime, timezone

class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── Lógica principal ─────────────────────────────────────────────────────
    async def get_userinfo(self, target: discord.User, guild: discord.Guild):

        # ─── Flags de la cuenta ───────────────────────────────────────────────
        flags = {
            'staff':               '👮 Discord Staff',
            'partner':             '🤝 Discord Partner',
            'hypesquad':           '🏠 HypeSquad Events',
            'bug_hunter':          '🐛 Bug Hunter',
            'hypesquad_bravery':   '🦁 HypeSquad Bravery',
            'hypesquad_brilliance':'💎 HypeSquad Brilliance',
            'hypesquad_balance':   '⚖️ HypeSquad Balance',
            'early_supporter':     '🌟 Early Supporter',
            'bug_hunter_level_2':  '🐛 Bug Hunter Level 2',
            'verified_bot':        '✅ Bot Verificado',
            'verified_bot_developer': '🔧 Developer Verificado',
            'active_developer':    '💻 Developer Activo'
        }

        user_flags = [label for flag, label in flags.items() if getattr(target.public_flags, flag, False)]

        # ─── Detección de multicuentas ────────────────────────────────────────
        account_age = (datetime.now(timezone.utc) - target.created_at).days
        warnings = []

        if account_age < 7:
            warnings.append('⚠️ Cuenta creada hace menos de 7 días')
        elif account_age < 30:
            warnings.append('⚠️ Cuenta creada hace menos de 30 días')

        if target.default_avatar == target.display_avatar:
            warnings.append('⚠️ Sin avatar personalizado')

        if target.bot:
            warnings.append('🤖 Es un bot')

        # ─── Construir embed ──────────────────────────────────────────────────
        embed = discord.Embed(
            title=f'👤 {target.name}',
            color=0xffffff,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(
            name='📋 Cuenta',
            value=f'**ID:** {target.id}\n**Creada:** <t:{int(target.created_at.timestamp())}:D>\n**Antigüedad:** {account_age} días',
            inline=False
        )

        embed.add_field(
            name='🏷️ Badges',
            value='\n'.join(user_flags) if user_flags else 'Ninguno',
            inline=False
        )

        # info del servidor si el usuario es miembro
        member = guild.get_member(target.id)
        if member:
            roles = [r.mention for r in member.roles if r.name != '@everyone']
            embed.add_field(
                name='🏠 En este servidor',
                value=f'**Entró:** <t:{int(member.joined_at.timestamp())}:D>\n**Roles:** {", ".join(roles) if roles else "Ninguno"}',
                inline=False
            )

        if warnings:
            embed.add_field(
                name='🚨 Alertas',
                value='\n'.join(warnings),
                inline=False
            )
            embed.color = 0xff9900

        embed.set_footer(text=f'Solicitado por un moderador')
        return embed

    # ─── Prefix command ───────────────────────────────────────────────────────
    @commands.command(name='userinfo', aliases=['ui', 'user'])
    async def userinfo_prefix(self, ctx, target: discord.User = None):
        target = target or ctx.author
        embed = await self.get_userinfo(target, ctx.guild)
        await ctx.reply(embed=embed)

    # ─── Slash command ────────────────────────────────────────────────────────
    @discord.slash_command(name='userinfo', description='Ver información de un usuario')
    async def userinfo_slash(self, ctx, usuario: discord.User = None):
        target = usuario or ctx.author
        embed = await self.get_userinfo(target, ctx.guild)
        await ctx.respond(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(UserInfo(bot))