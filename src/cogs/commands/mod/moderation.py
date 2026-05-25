import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import os


async def respond(ctx, **kwargs):
    """
    Helper universal para responder tanto en prefix como en slash commands.
    - ApplicationContext (slash) → ctx.respond()
    - Context (prefix)          → ctx.reply()
    """
    if isinstance(ctx, discord.ApplicationContext):
        await ctx.respond(**kwargs)
    else:
        await respond(ctx, **kwargs)


# ─── Helper: enviar log de moderación ─────────────────────────────────────────

async def send_mod_log(bot: commands.Bot, action: str, target: discord.User,
                       moderator: discord.User, reason: str, color: int,
                       extra: str = None):
    """
    Envía un embed al canal de logs de moderación.
    Llamado por todos los comandos de mod para dejar registro centralizado.
    """
    channel = bot.get_channel(int(os.getenv('MOD_LOG_CHANNEL_ID', 0)))
    if not channel:
        return

    embed = discord.Embed(
        title=f'🔨 {action}',
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name='Usuario', value=f'{target.mention} (`{target.id}`)', inline=True)
    embed.add_field(name='Moderador', value=f'{moderator.mention}', inline=True)
    embed.add_field(name='Razón', value=reason or 'Sin razón especificada', inline=False)
    if extra:
        embed.add_field(name='Info adicional', value=extra, inline=False)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text=f'ID: {target.id}')

    await channel.send(embed=embed)


# ─── Cog principal de moderación ──────────────────────────────────────────────

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── BAN ───────────────────────────────────────────────────────────────────

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx, member: discord.Member, *, reason: str = None):
        await self._ban(ctx, member, reason)

    @discord.slash_command(name='ban', description='Banear a un usuario del servidor')
    @commands.has_permissions(ban_members=True)
    async def ban_slash(self, ctx,
                        usuario: discord.Option(discord.Member, 'Usuario a banear'),
                        razon: discord.Option(str, 'Razón del ban', required=False)):
        await self._ban(ctx, usuario, razon)

    async def _ban(self, ctx, member: discord.Member, reason: str):
        # no puede banear a alguien con igual o mayor rol
        if member.top_role >= ctx.author.top_role:
            return await respond(ctx, embed=discord.Embed(
                description='❌ No puedes banear a alguien con igual o mayor rango que tú.',
                color=0xff0000
            ))
        if member == ctx.author:
            return await respond(ctx, embed=discord.Embed(
                description='❌ No puedes banearte a ti mismo.',
                color=0xff0000
            ))

        try:
            # intentar notificar al usuario por DM antes de banearlo
            try:
                await member.send(embed=discord.Embed(
                    description=f'🔨 Fuiste baneado de **{ctx.guild.name}**.\n**Razón:** {reason or "Sin razón especificada"}',
                    color=0xff0000
                ))
            except discord.Forbidden:
                pass  # el usuario tiene los DMs cerrados

            await member.ban(reason=reason, delete_message_days=1)
            await send_mod_log(self.bot, 'Ban', member, ctx.author, reason, 0xff0000)

            embed = discord.Embed(
                description=f'✅ {member.mention} fue baneado.',
                color=0xff0000
            )
            await respond(ctx, embed=embed)

        except discord.Forbidden:
            await respond(ctx, embed=discord.Embed(
                description='❌ No tengo permisos suficientes para banear a ese usuario.',
                color=0xff0000
            ))

    # ── UNBAN ─────────────────────────────────────────────────────────────────

    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban_prefix(self, ctx, user_id: int, *, reason: str = None):
        await self._unban(ctx, user_id, reason)

    @discord.slash_command(name='unban', description='Desbanear a un usuario por su ID')
    @commands.has_permissions(ban_members=True)
    async def unban_slash(self, ctx,
                          user_id: discord.Option(str, 'ID del usuario a desbanear'),
                          razon: discord.Option(str, 'Razón', required=False)):
        await self._unban(ctx, int(user_id), razon)

    async def _unban(self, ctx, user_id: int, reason: str):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
            await send_mod_log(self.bot, 'Unban', user, ctx.author, reason, 0x00ff99)
            await respond(ctx, embed=discord.Embed(
                description=f'✅ {user.mention} fue desbaneado.',
                color=0x00ff99
            ))
        except discord.NotFound:
            await respond(ctx, embed=discord.Embed(
                description='❌ Usuario no encontrado o no está baneado.',
                color=0xff0000
            ))

    # ── KICK ──────────────────────────────────────────────────────────────────

    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx, member: discord.Member, *, reason: str = None):
        await self._kick(ctx, member, reason)

    @discord.slash_command(name='kick', description='Expulsar a un usuario del servidor')
    @commands.has_permissions(kick_members=True)
    async def kick_slash(self, ctx,
                         usuario: discord.Option(discord.Member, 'Usuario a expulsar'),
                         razon: discord.Option(str, 'Razón', required=False)):
        await self._kick(ctx, usuario, razon)

    async def _kick(self, ctx, member: discord.Member, reason: str):
        if member.top_role >= ctx.author.top_role:
            return await respond(ctx, embed=discord.Embed(
                description='❌ No puedes expulsar a alguien con igual o mayor rango.',
                color=0xff0000
            ))

        try:
            try:
                await member.send(embed=discord.Embed(
                    description=f'👢 Fuiste expulsado de **{ctx.guild.name}**.\n**Razón:** {reason or "Sin razón especificada"}',
                    color=0xff9900
                ))
            except discord.Forbidden:
                pass

            await member.kick(reason=reason)
            await send_mod_log(self.bot, 'Kick', member, ctx.author, reason, 0xff9900)
            await respond(ctx, embed=discord.Embed(
                description=f'✅ {member.mention} fue expulsado.',
                color=0xff9900
            ))
        except discord.Forbidden:
            await respond(ctx, embed=discord.Embed(
                description='❌ No tengo permisos suficientes.',
                color=0xff0000
            ))

    # ── MUTE (timeout) ────────────────────────────────────────────────────────
    # Usa el timeout nativo de Discord en lugar de un rol separado.
    # El usuario sigue en el servidor pero no puede escribir ni hablar.

    @commands.command(name='mute')
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx, member: discord.Member, duration: str = '10m', *, reason: str = None):
        await self._mute(ctx, member, duration, reason)

    @discord.slash_command(name='mute', description='Silenciar a un usuario (timeout)')
    @commands.has_permissions(moderate_members=True)
    async def mute_slash(self, ctx,
                         usuario: discord.Option(discord.Member, 'Usuario a silenciar'),
                         duracion: discord.Option(str, 'Duración: 10m, 1h, 1d, 7d', default='10m'),
                         razon: discord.Option(str, 'Razón', required=False)):
        await self._mute(ctx, usuario, duracion, razon)

    async def _mute(self, ctx, member: discord.Member, duration: str, reason: str):
        if member.top_role >= ctx.author.top_role:
            return await respond(ctx, embed=discord.Embed(
                description='❌ No puedes silenciar a alguien con igual o mayor rango.',
                color=0xff0000
            ))

        # parsear la duración (ej: "10m", "1h", "2d")
        delta = parse_duration(duration)
        if not delta:
            return await respond(ctx, embed=discord.Embed(
                description='❌ Duración inválida. Usa: `10m`, `1h`, `1d`, `7d` (máximo 28 días)',
                color=0xff0000
            ))

        try:
            until = datetime.now(timezone.utc) + delta
            await member.timeout(until, reason=reason)
            await send_mod_log(self.bot, 'Mute', member, ctx.author, reason,
                               0xffcc00, extra=f'Duración: {duration}')
            await respond(ctx, embed=discord.Embed(
                description=f'🔇 {member.mention} fue silenciado por **{duration}**.',
                color=0xffcc00
            ))
        except discord.Forbidden:
            await respond(ctx, embed=discord.Embed(
                description='❌ No tengo permisos suficientes.',
                color=0xff0000
            ))

    # ── UNMUTE ────────────────────────────────────────────────────────────────

    @commands.command(name='unmute')
    @commands.has_permissions(moderate_members=True)
    async def unmute_prefix(self, ctx, member: discord.Member, *, reason: str = None):
        await self._unmute(ctx, member, reason)

    @discord.slash_command(name='unmute', description='Quitar el silencio a un usuario')
    @commands.has_permissions(moderate_members=True)
    async def unmute_slash(self, ctx,
                           usuario: discord.Option(discord.Member, 'Usuario a des-silenciar'),
                           razon: discord.Option(str, 'Razón', required=False)):
        await self._unmute(ctx, usuario, razon)

    async def _unmute(self, ctx, member: discord.Member, reason: str):
        try:
            await member.timeout(None, reason=reason)
            await send_mod_log(self.bot, 'Unmute', member, ctx.author, reason, 0x00ff99)
            await respond(ctx, embed=discord.Embed(
                description=f'🔊 {member.mention} ya puede hablar nuevamente.',
                color=0x00ff99
            ))
        except discord.Forbidden:
            await respond(ctx, embed=discord.Embed(
                description='❌ No tengo permisos suficientes.',
                color=0xff0000
            ))

    # ── WARN ──────────────────────────────────────────────────────────────────

    @commands.command(name='warn')
    @commands.has_permissions(kick_members=True)
    async def warn_prefix(self, ctx, member: discord.Member, *, reason: str = None):
        await self._warn(ctx, member, reason)

    @discord.slash_command(name='warn', description='Advertir a un usuario')
    @commands.has_permissions(kick_members=True)
    async def warn_slash(self, ctx,
                         usuario: discord.Option(discord.Member, 'Usuario a advertir'),
                         razon: discord.Option(str, 'Razón de la advertencia', required=False)):
        await self._warn(ctx, usuario, razon)

    async def _warn(self, ctx, member: discord.Member, reason: str):
        try:
            await member.send(embed=discord.Embed(
                description=f'⚠️ Recibiste una advertencia en **{ctx.guild.name}**.\n**Razón:** {reason or "Sin razón especificada"}',
                color=0xffcc00
            ))
        except discord.Forbidden:
            pass

        await send_mod_log(self.bot, 'Warn', member, ctx.author, reason, 0xffcc00)
        await respond(ctx, embed=discord.Embed(
            description=f'⚠️ {member.mention} fue advertido.',
            color=0xffcc00
        ))

    # ── PURGE ─────────────────────────────────────────────────────────────────

    @commands.command(name='purge', aliases=['clear'])
    @commands.has_permissions(manage_messages=True)
    async def purge_prefix(self, ctx, amount: int = 10):
        await self._purge(ctx, amount)

    @discord.slash_command(name='purge', description='Eliminar mensajes en masa')
    @commands.has_permissions(manage_messages=True)
    async def purge_slash(self, ctx,
                          cantidad: discord.Option(int, 'Cantidad de mensajes a eliminar (máx 100)', default=10)):
        await self._purge(ctx, cantidad)

    async def _purge(self, ctx, amount: int):
        if amount < 1 or amount > 100:
            return await respond(ctx, embed=discord.Embed(
                description='❌ La cantidad debe ser entre 1 y 100.',
                color=0xff0000
            ))

        # para prefix: borrar también el mensaje del comando
        is_slash = isinstance(ctx, discord.ApplicationContext)
        if is_slash:
            await ctx.defer(ephemeral=True)

        deleted = await ctx.channel.purge(limit=amount)

        msg = await ctx.channel.send(embed=discord.Embed(
            description=f'🗑️ {len(deleted)} mensaje(s) eliminado(s).',
            color=0xffffff
        ))
        # auto-eliminar la confirmación después de 3 segundos
        await discord.utils.sleep_until(datetime.now(timezone.utc) + timedelta(seconds=3))
        try:
            await msg.delete()
        except discord.NotFound:
            pass

        if is_slash:
            await ctx.respond('✅ Listo.', ephemeral=True)

    # ── SLOWMODE ──────────────────────────────────────────────────────────────

    @commands.command(name='slowmode')
    @commands.has_permissions(manage_channels=True)
    async def slowmode_prefix(self, ctx, seconds: int = 0):
        await self._slowmode(ctx, seconds)

    @discord.slash_command(name='slowmode', description='Configurar slowmode en el canal')
    @commands.has_permissions(manage_channels=True)
    async def slowmode_slash(self, ctx,
                             segundos: discord.Option(int, 'Segundos entre mensajes (0 = desactivar)', default=0)):
        await self._slowmode(ctx, segundos)

    async def _slowmode(self, ctx, seconds: int):
        if seconds < 0 or seconds > 21600:
            return await respond(ctx, embed=discord.Embed(
                description='❌ El slowmode debe estar entre 0 y 21600 segundos (6 horas).',
                color=0xff0000
            ))

        await ctx.channel.edit(slowmode_delay=seconds)

        if seconds == 0:
            desc = '✅ Slowmode desactivado.'
        else:
            desc = f'✅ Slowmode configurado a **{seconds}s**.'

        await respond(ctx, embed=discord.Embed(description=desc, color=0xffffff))

    # ── LOCK CHANNEL ──────────────────────────────────────────────────────────

    @commands.command(name='lockdown', aliases=['lock'])
    @commands.has_permissions(manage_channels=True)
    async def lockdown_prefix(self, ctx, *, reason: str = None):
        await self._lockdown(ctx, reason)

    @discord.slash_command(name='lockdown', description='Bloquear el canal actual para todos')
    @commands.has_permissions(manage_channels=True)
    async def lockdown_slash(self, ctx,
                             razon: discord.Option(str, 'Razón', required=False)):
        await self._lockdown(ctx, razon)

    async def _lockdown(self, ctx, reason: str):
        # denegar envío de mensajes al rol @everyone en este canal
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                                          reason=reason)
        await respond(ctx, embed=discord.Embed(
            description=f'🔒 Canal bloqueado. {f"**Razón:** {reason}" if reason else ""}',
            color=0xff0000
        ))

    @commands.command(name='unlock')
    @commands.has_permissions(manage_channels=True)
    async def unlock_prefix(self, ctx):
        await self._unlock(ctx)

    @discord.slash_command(name='unlock', description='Desbloquear el canal actual')
    @commands.has_permissions(manage_channels=True)
    async def unlock_slash(self, ctx):
        await self._unlock(ctx)

    async def _unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None  # None = heredar del servidor
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await respond(ctx, embed=discord.Embed(
            description='🔓 Canal desbloqueado.',
            color=0x00ff99
        ))

    # ── MANEJO DE ERRORES DE PERMISOS ─────────────────────────────────────────

    @ban_prefix.error
    @kick_prefix.error
    @mute_prefix.error
    @warn_prefix.error
    @purge_prefix.error
    @slowmode_prefix.error
    @lockdown_prefix.error
    @unlock_prefix.error
    @unmute_prefix.error
    @unban_prefix.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await respond(ctx, embed=discord.Embed(
                description='❌ No tienes permisos para usar este comando.',
                color=0xff0000
            ))
        elif isinstance(error, commands.MemberNotFound):
            await respond(ctx, embed=discord.Embed(
                description='❌ Usuario no encontrado.',
                color=0xff0000
            ))
        elif isinstance(error, commands.BadArgument):
            await respond(ctx, embed=discord.Embed(
                description='❌ Argumento inválido.',
                color=0xff0000
            ))


# ─── Helper: parsear duración ─────────────────────────────────────────────────

def parse_duration(duration: str) -> timedelta | None:
    """
    Convierte un string de duración a timedelta.
    Formatos soportados: 10m, 1h, 1d, 7d (máximo 28d por límite de Discord).
    Retorna None si el formato es inválido.
    """
    units = {'m': 'minutes', 'h': 'hours', 'd': 'days'}
    if not duration or len(duration) < 2:
        return None

    unit = duration[-1].lower()
    if unit not in units:
        return None

    try:
        value = int(duration[:-1])
    except ValueError:
        return None

    if value <= 0:
        return None

    delta = timedelta(**{units[unit]: value})

    # Discord limita el timeout a 28 días
    if delta > timedelta(days=28):
        return None

    return delta


def setup(bot: commands.Bot):
    bot.add_cog(Moderation(bot))