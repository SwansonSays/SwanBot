import os
import discord, logging
from dotenv import load_dotenv
from discord.ext import commands
import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

join_time = -1
leave_time = -1

#Event handling
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_voice_state_update(member, before, after):
    #Logs to console on voice channel join
    if before.channel == None and after.channel != None:
        join_time = datetime.datetime.now()
        print(f'{member} JOINED {before.channel} @ {join_time}')
        print(f'Hello {member}!')

    #Logs to console on voice channel leave
    if before.channel != None and after.channel == None:
        leave_time = datetime.datetime.now()
        print(f'{member.name} LEFT {before.channel} @ {leave_time}')

        #Sends msg to general text channel on voice channel leave
        channel = bot.get_channel(784337067307302914)
        await channel.send("HII")

#Command handling
@bot.command()
async def echo(ctx, *args):
    arguments = ' '.join(args)
    await ctx.send(arguments)

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.message.author}!')


bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)