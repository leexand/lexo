import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import os
import re

# ─── Configuración del automod ────────────────────────────────────────────────
# Estos valores se pueden mover al .env si quieres hacerlos configurables
# sin tocar el código.

SPAM_MESSAGE_LIMIT = 5        # mensajes máximos en la ventana de tiempo
SPAM_TIME_WINDOW   = 5        # segundos de la ventana para detectar spam
SPAM_MUTE_DURATION = 5        # minutos de timeout al detectar spam

MENTION_LIMIT = 5             # menciones máximas por mensaje
RAID_JOIN_LIMIT = 10          # usuarios máximos entrando en la ventana de raid
RAID_TIME_WINDOW = 10         # segundos de ventana para detectar raid
RAID_VERIFICATION_LEVEL = discord.VerificationLevel.high  # nivel al activar anti-raid

# Dominios permitidos para postear links (whitelist).
# Todo lo demás será bloqueado si el usuario no tiene manage_messages.
ALLOWED_DOMAINS = [
    'discord.com',
    'discord.gg',
    'youtube.com',
    'youtu.be',
    'twitter.com',
    'x.com',
    'github.com',
]

# Palabras prohibidas — añadir las que quieras
BANNED_WORDS = ['pipi']

# Regex para detectar URLs
URL_REGEX = re.compile(r'https?://[^\s]+|www\.[^\s]+', re.IGNORECASE)


class Automod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # historial de mensajes recientes por usuario: {user_id: [timestamps]}
        self._message_times: dict[int, list[datetime]] = defaultdict(list)

        # timestamps de joins recientes para detección de raids: [datetime]
        self._recent_joins: list[datetime] = []

        # flag de raid activo para no activarlo múltiples veces
        self._raid_active = False

        # tarea de limpieza periódica del historial de spam
        self._cleanup_task = bot.loop.create_task(self._cleanup_loop())

    # ─── DETECCIÓN DE SPAM ────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignorar bots y DMs
        if message.author.bot or not message.guild:
            return

        # staff con manage_messages está exento del automod
        if message.author.guild_permissions.manage_messages:
            return

        # verificar cada regla en orden — la primera que dispara corta el resto
        if await self._check_banned_words(message):
            return
        if await self._check_links(message):
            return
        if await self._check_mentions(message):
            return
        await self._check_spam(message)

    async def _check_spam(self, message: discord.Message):
        """
        Detecta si un usuario envió demasiados mensajes en poco tiempo.
        Si supera el límite, elimina los mensajes recientes y aplica timeout.
        """
        now = datetime.now(timezone.utc)
        uid = message.author.id

        # agregar timestamp del mensaje actual y limpiar los viejos
        self._message_times[uid].append(now)
        cutoff = now - timedelta(seconds=SPAM_TIME_WINDOW)
        self._message_times[uid] = [t for t in self._message_times[uid] if t > cutoff]

        if len(self._message_times[uid]) >= SPAM_MESSAGE_LIMIT:
            # limpiar historial para no volver a disparar inmediatamente
            self._message_times[uid] = []

            # aplicar timeout
            try:
                until = now + timedelta(minutes=SPAM_MUTE_DURATION)
                await message.author.timeout(until, reason='[Automod] Spam detectado')
            except discord.Forbidden:
                pass

            # activar slowmode temporalmente en el canal
            try:
                await message.channel.edit(slowmode_delay=10)
                # quitar el slowmode después de 60 segundos
                asyncio.create_task(self._remove_slowmode(message.channel, 60))
            except discord.Forbidden:
                pass

            await self._log_automod(
                action='Spam',
                user=message.author,
                channel=message.channel,
                detail=f'{SPAM_MESSAGE_LIMIT} mensajes en {SPAM_TIME_WINDOW}s → timeout {SPAM_MUTE_DURATION}m + slowmode',
                color=0xff9900
            )

    async def _check_mentions(self, message: discord.Message):
        """
        Elimina mensajes con demasiadas menciones y aplica timeout al autor.
        """
        total_mentions = len(message.mentions) + len(message.role_mentions)
        if total_mentions < MENTION_LIMIT:
            return False

        try:
            await message.delete()
        except discord.NotFound:
            pass

        try:
            until = datetime.now(timezone.utc) + timedelta(minutes=10)
            await message.author.timeout(until, reason='[Automod] Mención masiva')
        except discord.Forbidden:
            pass

        await self._log_automod(
            action='Mención masiva',
            user=message.author,
            channel=message.channel,
            detail=f'{total_mentions} menciones en un mensaje',
            color=0xff0000
        )
        return True

    async def _check_links(self, message: discord.Message):
        """
        Elimina mensajes con links de dominios no permitidos.
        """
        urls = URL_REGEX.findall(message.content)
        if not urls:
            return False

        for url in urls:
            # extraer el dominio de la URL
            domain = url.split('/')[2] if '//' in url else url.split('/')[0]
            domain = domain.lstrip('www.').lower()

            if not any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass

                await self._log_automod(
                    action='Link bloqueado',
                    user=message.author,
                    channel=message.channel,
                    detail=f'URL no permitida: `{url[:100]}`',
                    color=0xff9900
                )
                return True

        return False

    async def _check_banned_words(self, message: discord.Message):
        """
        Elimina mensajes que contengan palabras de la lista negra.
        """
        if not BANNED_WORDS:
            return False

        content_lower = message.content.lower()
        for word in BANNED_WORDS:
            if word.lower() in content_lower:
                try:
                    await message.delete()
                except discord.NotFound:
                    pass

                await self._log_automod(
                    action='Palabra prohibida',
                    user=message.author,
                    channel=message.channel,
                    detail=f'Palabra detectada en el mensaje',
                    color=0xff0000
                )
                return True

        return False

    # ─── DETECCIÓN DE RAIDS ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Monitorea la velocidad de joins para detectar raids.
        Si muchos usuarios entran en poco tiempo, activa el modo anti-raid:
        sube el nivel de verificación del servidor temporalmente.
        """
        now = datetime.now(timezone.utc)
        self._recent_joins.append(now)

        # limpiar joins viejos fuera de la ventana
        cutoff = now - timedelta(seconds=RAID_TIME_WINDOW)
        self._recent_joins = [t for t in self._recent_joins if t > cutoff]

        if len(self._recent_joins) >= RAID_JOIN_LIMIT and not self._raid_active:
            self._raid_active = True
            await self._activate_antiraid(member.guild)

    async def _activate_antiraid(self, guild: discord.Guild):
        """
        Sube el nivel de verificación del servidor y notifica al canal de logs.
        Revierte automáticamente después de 5 minutos.
        """
        try:
            original_level = guild.verification_level
            await guild.edit(
                verification_level=RAID_VERIFICATION_LEVEL,
                reason='[Automod] Raid detectado'
            )

            channel = self.bot.get_channel(int(os.getenv('MOD_LOG_CHANNEL_ID', 0)))
            if channel:
                await channel.send(embed=discord.Embed(
                    title='🚨 Raid detectado',
                    description=(
                        f'{RAID_JOIN_LIMIT} usuarios entraron en {RAID_TIME_WINDOW}s.\n'
                        f'Nivel de verificación subido a **{RAID_VERIFICATION_LEVEL.name}**.\n'
                        f'Se revertirá en **5 minutos** automáticamente.'
                    ),
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                ))

            # revertir después de 5 minutos
            await asyncio.sleep(300)
            await guild.edit(
                verification_level=original_level,
                reason='[Automod] Anti-raid desactivado automáticamente'
            )

            if channel:
                await channel.send(embed=discord.Embed(
                    description='✅ Nivel de verificación revertido. Anti-raid desactivado.',
                    color=0x00ff99
                ))

        except discord.Forbidden:
            pass
        finally:
            self._raid_active = False
            self._recent_joins = []

    # ─── LOGS DE EDICIÓN Y ELIMINACIÓN DE MENSAJES ───────────────────────────

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Registra ediciones de mensajes en el canal de logs.
        Ignora bots y mensajes donde el contenido no cambió (ej: embeds que se cargan).
        """
        if before.author.bot or before.content == after.content:
            return

        channel = self.bot.get_channel(int(os.getenv('MSG_LOG_CHANNEL_ID', 0)))
        if not channel:
            return

        embed = discord.Embed(
            title='✏️ Mensaje editado',
            color=0x5865f2,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Autor', value=before.author.mention, inline=True)
        embed.add_field(name='Canal', value=before.channel.mention, inline=True)
        embed.add_field(name='Antes', value=before.content[:1024] or '*vacío*', inline=False)
        embed.add_field(name='Después', value=after.content[:1024] or '*vacío*', inline=False)
        embed.add_field(name='Ir al mensaje', value=f'[Click aquí]({after.jump_url})', inline=False)
        embed.set_footer(text=f'ID del mensaje: {before.id}')

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """
        Registra eliminaciones de mensajes en el canal de logs.
        """
        if message.author.bot:
            return

        channel = self.bot.get_channel(int(os.getenv('MSG_LOG_CHANNEL_ID', 0)))
        if not channel:
            return

        embed = discord.Embed(
            title='🗑️ Mensaje eliminado',
            color=0xff4444,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Autor', value=message.author.mention, inline=True)
        embed.add_field(name='Canal', value=message.channel.mention, inline=False)
        embed.add_field(name='Contenido', value=message.content[:1024] or '*sin contenido de texto*', inline=False)
        embed.set_footer(text=f'ID: {message.id}')

        await channel.send(embed=embed)

    # ─── LOGS DE MIEMBROS ─────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        Registra cuando alguien sale o es expulsado del servidor.
        """
        channel = self.bot.get_channel(int(os.getenv('MEMBER_LOG_CHANNEL_ID', 0)))
        if not channel:
            return

        embed = discord.Embed(
            title='📤 Miembro salió',
            color=0xff9900,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name='Usuario', value=f'{member.mention} (`{member.id}`)', inline=False)
        embed.add_field(name='Entró', value=f'<t:{int(member.joined_at.timestamp())}:R>' if member.joined_at else 'Desconocido', inline=True)
        roles = [r.mention for r in member.roles if r.name != '@everyone']
        embed.add_field(name='Roles', value=', '.join(roles) if roles else 'Ninguno', inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Registra cambios de roles en el canal de logs.
        """
        if before.roles == after.roles:
            return

        channel = self.bot.get_channel(int(os.getenv('MEMBER_LOG_CHANNEL_ID', 0)))
        if not channel:
            return

        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]

        if not added and not removed:
            return

        embed = discord.Embed(
            title='🏷️ Roles actualizados',
            color=0x5865f2,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Usuario', value=after.mention, inline=False)
        if added:
            embed.add_field(name='Roles agregados', value=' '.join(r.mention for r in added), inline=False)
        if removed:
            embed.add_field(name='Roles removidos', value=' '.join(r.mention for r in removed), inline=False)

        await channel.send(embed=embed)

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    async def _log_automod(self, action: str, user: discord.Member,
                           channel: discord.TextChannel, detail: str, color: int):
        """
        Envía un embed al canal de logs del automod.
        """
        log_channel = self.bot.get_channel(int(os.getenv('MOD_LOG_CHANNEL_ID', 0)))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f'🤖 Automod — {action}',
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name='Usuario', value=f'{user.mention} (`{user.id}`)', inline=True)
        embed.add_field(name='Canal', value=channel.mention, inline=True)
        embed.add_field(name='Detalle', value=detail, inline=False)
        embed.set_footer(text=f'ID: {user.id}')

        await log_channel.send(embed=embed)

    async def _remove_slowmode(self, channel: discord.TextChannel, delay: int):
        """Quita el slowmode de un canal después de `delay` segundos."""
        await asyncio.sleep(delay)
        try:
            await channel.edit(slowmode_delay=0)
        except discord.Forbidden:
            pass

    async def _cleanup_loop(self):
        """
        Limpia el historial de spam cada 60 segundos para evitar que
        el diccionario crezca indefinidamente en servidores grandes.
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(60)
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=SPAM_TIME_WINDOW * 2)
            to_delete = [uid for uid, times in self._message_times.items()
                         if not times or max(times) < cutoff]
            for uid in to_delete:
                del self._message_times[uid]

    def cog_unload(self):
        """Cancela la tarea de limpieza al descargar el cog."""
        self._cleanup_task.cancel()


def setup(bot: commands.Bot):
    bot.add_cog(Automod(bot))