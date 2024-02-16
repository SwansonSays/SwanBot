import os
import discord, logging
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

#Event handling
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

#Command handling
@bot.command()
async def echo(ctx, *args):
    arguments = ' '.join(args)
    await ctx.send(arguments)

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.message.author}!')


bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)