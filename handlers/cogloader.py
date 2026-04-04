import os 
import discord
from discord.ext import commands
async def load_cogs(bot):
    """
    Carga todos los cogs desde src/cogs de forma recursiva
    Busca archivos .py en todas las subcarpetas
    """
    loaded = 0
    errors = 0
    
    for root, dirs, files in os.walk('src/cogs'):
        for file in files:
            if not file.endswith('.py'):
                continue

            # convertir ruta de archivo a notación de módulo
            # ej: src/cogs/events/ready.py -> src.cogs.events.ready
            path = os.path.join(root, file)
            module = path.replace(os.sep, '.').replace('/', '.').removesuffix('.py')

            try:
                bot.load_extension(module)
                loaded += 1
                print(f'[COGLOADER] ✅ {module}')
            except Exception as e:
                errors += 1
                print(f'[COGLOADER] ❌ {module} — {e}')

    print(f'[COGLOADER] {loaded} cogs cargados, {errors} errores')