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

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    await bot.process_commands(message)


@bot.command()
async def test(ctx, arg):
    await ctx.send(f'This bitch said {arg}')

@bot.command()
async def echo(ctx, *args):
    arguments = ' '.join(args)
    await ctx.send(arguments)


bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)