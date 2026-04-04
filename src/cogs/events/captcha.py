import discord
from discord.ext import commands
import random
import string
import os
from PIL import Image, ImageDraw, ImageFilter
import io

def generate_captcha():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    img = Image.new('RGB', (200, 80), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    # líneas de ruido
    for _ in range(8):
        x1, y1 = random.randint(0, 200), random.randint(0, 80)
        x2, y2 = random.randint(0, 200), random.randint(0, 80)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)), width=1)

    # puntos de ruido
    for _ in range(200):
        x, y = random.randint(0, 200), random.randint(0, 80)
        draw.point((x, y), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))

    draw.text((30, 25), code, fill=(255, 255, 255))

    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return code, buffer

def setup(bot: commands.Bot):
    bot.add_cog(Captcha(bot))

# ─── Botón para abrir el modal ────────────────────────────────────────────────
class CodeButton(discord.ui.View):
    def __init__(self, code: str):
        super().__init__(timeout=180) # expira en 3 minutos
        self.code = code

    @discord.ui.button(label='Ingresar código', style=discord.ButtonStyle.secondary, emoji='⌨️')
    async def enter_code(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(CaptchaModal(self.code))

# ─── Modal ────────────────────────────────────────────────────────────────────
class CaptchaModal(discord.ui.Modal):
    def __init__(self, code: str):
        self.code = code
        super().__init__(title='Verificación')

        self.add_item(
            discord.ui.InputText(
                label='Escribe el código de la imagen',
                placeholder='Ej: A3K9PZ',
                min_length=6,
                max_length=6
            )
        )

    async def callback(self, interaction: discord.Interaction):
        user_input = self.children[0].value.upper().strip()

        if user_input == self.code:
            # ── Verificación exitosa ──────────────────────────────────────────
            delRole = interaction.guild.get_role(int(os.getenv('UNVERIFIED_ROLE_ID')))
            addRole = interaction.guild.get_role(int(os.getenv('VERIFIED_ROLE_ID')))
            if delRole and addRole:
                await interaction.user.remove_roles(delRole)
                await interaction.user.add_roles(addRole)

            # mensaje de bienvenida
            welcome_channel = interaction.client.get_channel(int(os.getenv('WELCOME_CHANNEL_ID')))
            if welcome_channel:
                await welcome_channel.send(
                    content=f'👋 ¡Bienvenido/a al servidor {interaction.user.mention}!'
                )

            await interaction.response.send_message(
                '✅ ¡Verificado! Ya tienes acceso al servidor.',
                ephemeral=True
            )

        else:
            # ── Código incorrecto — generar nuevo captcha ─────────────────────
            new_code, new_image = generate_captcha()
            self.code = new_code

            await interaction.response.send_message(
                '❌ Código incorrecto, inténtalo de nuevo:',
                file=discord.File(new_image, filename='captcha.png'),
                view=CodeButton(new_code),
                ephemeral=True
            )

    async def on_error(self, error: Exception, interaction: discord.Interaction):
        print(f'[Captcha] Error: {error}')
        await interaction.response.send_message('⚠️ Hubo un error, inténtalo de nuevo.', ephemeral=True)

class Captcha(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot