import discord
from discord.ext import commands
from datetime import datetime, timezone
import os


class ChannelLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _log_channel(self):
        """Retorna el canal de logs de canales configurado en .env."""
        channel_id = os.getenv('CHANNEL_LOG_CHANNEL_ID')
        if not channel_id:
            return None
        return self.bot.get_channel(int(channel_id))

    # ─── CANAL CREADO ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log = self._log_channel()
        if not log:
            return

        tipo = _channel_type(channel)

        embed = discord.Embed(
            title='🟢 Canal creado',
            color=0x00ff99,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Canal', value=f'{channel.mention} (`{channel.id}`)', inline=True)
        embed.add_field(name='Tipo', value=tipo, inline=True)
        if channel.category:
            embed.add_field(name='Categoría', value=channel.category.name, inline=True)
        embed.set_footer(text=f'ID: {channel.id}')

        await log.send(embed=embed)

    # ─── CANAL ELIMINADO ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log = self._log_channel()
        if not log:
            return

        tipo = _channel_type(channel)

        embed = discord.Embed(
            title='🔴 Canal eliminado',
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Canal', value=f'`#{channel.name}` (`{channel.id}`)', inline=True)
        embed.add_field(name='Tipo', value=tipo, inline=True)
        if channel.category:
            embed.add_field(name='Categoría', value=channel.category.name, inline=True)
        embed.set_footer(text=f'ID: {channel.id}')

        await log.send(embed=embed)

    # ─── CANAL EDITADO ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        log = self._log_channel()
        if not log:
            return

        changes = []

        # nombre
        if before.name != after.name:
            changes.append(f'**Nombre:** `{before.name}` → `{after.name}`')

        # categoría
        if before.category != after.category:
            b = before.category.name if before.category else 'Sin categoría'
            a = after.category.name if after.category else 'Sin categoría'
            changes.append(f'**Categoría:** `{b}` → `{a}`')

        # slowmode (solo texto)
        if isinstance(before, discord.TextChannel) and before.slowmode_delay != after.slowmode_delay:
            changes.append(f'**Slowmode:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`')

        # límite de usuarios (solo voz)
        if isinstance(before, discord.VoiceChannel) and before.user_limit != after.user_limit:
            b_limit = str(before.user_limit) if before.user_limit else 'Sin límite'
            a_limit = str(after.user_limit) if after.user_limit else 'Sin límite'
            changes.append(f'**Límite de usuarios:** `{b_limit}` → `{a_limit}`')

        # permisos
        if before.overwrites != after.overwrites:
            changes.append('**Permisos:** modificados')

        # nsfw
        if isinstance(before, discord.TextChannel) and before.nsfw != after.nsfw:
            changes.append(f'**NSFW:** `{before.nsfw}` → `{after.nsfw}`')

        if not changes:
            return

        embed = discord.Embed(
            title='✏️ Canal editado',
            color=0x5865f2,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Canal', value=after.mention, inline=True)
        embed.add_field(name='Tipo', value=_channel_type(after), inline=True)
        embed.add_field(name='Cambios', value='\n'.join(changes), inline=False)
        embed.set_footer(text=f'ID: {after.id}')

        await log.send(embed=embed)

    # ─── VOZ: ALGUIEN ENTRA, SALE O SE MUEVE ─────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        log = self._log_channel()
        if not log:
            return

        # ignorar cambios que no sean de canal (ej: activar cámara, mutear)
        if before.channel == after.channel:
            return

        # ── entró a un canal de voz ────────────────────────────────────────────
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title='🔊 Entró a voz',
                color=0x00ff99,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name='Usuario', value=f'{member.mention} (`{member.id}`)', inline=True)
            embed.add_field(name='Canal', value=after.channel.mention, inline=True)

        # ── salió de un canal de voz ───────────────────────────────────────────
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title='🔇 Salió de voz',
                color=0xff4444,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name='Usuario', value=f'{member.mention} (`{member.id}`)', inline=True)
            embed.add_field(name='Canal', value=before.channel.mention, inline=True)

        # ── se movió de un canal a otro ────────────────────────────────────────
        else:
            embed = discord.Embed(
                title='🔀 Se movió de canal',
                color=0x5865f2,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name='Usuario', value=f'{member.mention} (`{member.id}`)', inline=True)
            embed.add_field(name='Desde', value=before.channel.mention, inline=True)
            embed.add_field(name='Hacia', value=after.channel.mention, inline=True)

        embed.set_footer(text=f'ID: {member.id}')
        await log.send(embed=embed)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _channel_type(channel: discord.abc.GuildChannel) -> str:
    """Retorna una etiqueta legible del tipo de canal."""
    types = {
        discord.TextChannel:     '💬 Texto',
        discord.VoiceChannel:    '🔊 Voz',
        discord.CategoryChannel: '📁 Categoría',
        discord.StageChannel:    '🎙️ Escenario',
        discord.ForumChannel:    '📋 Foro',
    }
    return types.get(type(channel), '❓ Desconocido')


def setup(bot: commands.Bot):
    bot.add_cog(ChannelLogs(bot))