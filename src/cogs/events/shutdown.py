import discord
from discord.ext import commands
from datetime import datetime, timezone
import os
import asyncio
import signal

class Shutdown(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # escuchar señales del sistema para cierre controlado
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        self.bot.loop.create_task(self.shutdown())

    async def shutdown(self):
        print('[SHUTDOWN] Procesando cierre..')
        try:
            # limpiar mensaje de inicio del canal de logs
            channel = self.bot.get_channel(int(os.getenv('START_CHANNEL_ID')))
            if channel:
                async for msg in channel.history(limit=1):
                    await msg.delete()

            # enviar mensaje de apagado por webhook
            webhook = discord.SyncWebhook.from_url(os.getenv('SHUTDOWN_WEBHOOK_URL'))
            webhook.send(
                username=self.bot.user.name,
                avatar_url=str(self.bot.user.display_avatar.url),
                embed=discord.Embed(
                    title=f'🔴 Apagado de {self.bot.user.name}',
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                )
                .add_field(name='Estado', value='Inactivo', inline=True)
                .set_footer(text=f'Creado por {os.getenv("DEV")}')
            )

            print('[SHUTDOWN] Webhook enviado')

        except Exception as e:
            print(f'[SHUTDOWN] Error: {e}')
        finally:
            await self.bot.close()
            await asyncio.sleep(0.5) # dar tiempo a que las sesiones cierren
            print('[SHUTDOWN] Cliente desconectado')
            print('[SHUTDOWN] Procesando cierre..')
            try:
                # limpiar mensaje de inicio del canal de logs
                channel = self.bot.get_channel(int(os.getenv('START_CHANNEL_ID')))
                if channel:
                    async for msg in channel.history(limit=1):
                        await msg.delete()

                # enviar mensaje de apagado por webhook
                webhook = discord.SyncWebhook.from_url(os.getenv('SHUTDOWN_WEBHOOK_URL'))
                webhook.send(
                    username=self.bot.user.name,
                    avatar_url=str(self.bot.user.display_avatar.url),
                    embed=discord.Embed(
                        title=f'🔴 Apagado de {self.bot.user.name}',
                        color=0xff0000,
                        timestamp=datetime.now(timezone.utc)
                    )
                    .add_field(name='Estado', value='Inactivo', inline=True)
                    .set_footer(text=f'Creado por {os.getenv("DEV")}')
                )

                print('[SHUTDOWN] Webhook enviado')

            except Exception as e:
                print(f'[SHUTDOWN] Error: {e}')
            finally:
                await self.bot.close()
                print('[SHUTDOWN] Cliente desconectado')

def setup(bot: commands.Bot):
    bot.add_cog(Shutdown(bot))