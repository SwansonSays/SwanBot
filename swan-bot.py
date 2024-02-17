import os
import datetime
import logging

import discord
from discord.ext import commands

from dotenv import load_dotenv

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_ID = os.getenv("DB_ID")
DB_KEY = os.getenv("DB_KEY")

#TODO figure out how to send err's to console but debug statements to log
#handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

#Connect to DB
uri = f"mongodb+srv://{DB_ID}:{DB_KEY}@cluster0.nvkklff.mongodb.net/?retryWrites=true&w=majority"
cluster = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    cluster.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

    
db = cluster["swanbot"]
collection = db["money"]
voice_collection = db["voice_join"]

#Event handling
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

#Greats new user and gives them 1000 coins on server join
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(784337067307302914) #hard coded general channel
    await channel.send(f"Welcome to the Server {member.name}")
    
    myquery = {"_id": member.id}
    if(collection.count_documents(myquery) == 0):
        post = {"_id": member.id, "money": 1000}
        collection.insert_one(post)
        print(f"Your Starting Balance is $1000!")

#Gives coins for every 30 minutes user is in voice call
@bot.event
async def on_voice_state_update(member, before, after):
    #Puts Join time into DB when VC is joined
    if before.channel == None and after.channel != None:
        join_time = datetime.datetime.now()
        #print(f'{member} JOINED {before.channel} @ {join_time}')
        #print(f'Hello {member}!')

        query = {"_id": member.id}
        if(voice_collection.count_documents(query) == 0):
            post = {"_id": member.id, "join_time": join_time}
            voice_collection.insert_one(post)
        else:
            voice_collection.update_one({"_id": member.id}, {"$set":{"join_time": join_time}})

    #Pull join_time from DB and calculates money earned for total time in VC
    if before.channel != None and after.channel == None:
        leave_time = datetime.datetime.now()
        #print(f'{member.name} LEFT {before.channel} @ {leave_time}')

        query = {"_id": member.id}
        user = voice_collection.find(query)
        for result in user:
            join_time = result["join_time"]

        #User earns 50 coins for every half hour they are in VC
        total_seconds = (leave_time - join_time).total_seconds()
        money_earned = int(total_seconds / 1800 * 50)

        user = collection.find(query)
        for result in user:
            money = int(result["money"])

        money = money + money_earned
        collection.update_one({"_id": member.id}, {"$set":{"money": money}})

        channel = bot.get_channel(784337067307302914) #hard coded general channel
        await channel.send(f"{member.name} earned {money_earned} coins for beining in {before.channel}.\nYour new balance is {money}.")



#Command handling
        
#echo response
@bot.command()
async def echo(ctx, *args):
    arguments = ' '.join(args)
    await ctx.send(arguments)

#Greats user who send command
@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author}!')

#Give money to anyone. In future admin use only or helper function only
@bot.command()
async def selfGive(ctx, value):
    value = int(value)
    myquery = {"_id": ctx.author.id}

    if(collection.count_documents(myquery) == 0):
        if value > 0:
            post = {"_id": ctx.author.id, "money": value}
            collection.insert_one(post)
            print(f"{value} given to {ctx.author}(id: {ctx.author.id})")
            print(f"{ctx.author}'s new balance is {money}")
    else :
        print("Not Equal 0")
        if value > 0:
            query = {"_id": ctx.author.id}
            user = collection.find(query)
            for result in user:
                money = int(result["money"])
            money = money + value
            collection.update_one({"_id": ctx.author.id}, {"$set":{"money": money}})
            print(f"{value} given to {ctx.message.author}(id: {ctx.author.id}")
            print(f"{ctx.author}'s new balance is {money}")
            await ctx.send(f"{ctx.author}'s new balance is {money}")

#shows balance of user who sends command. In future be able to check anyones balance
@bot.command()
async def balance(ctx):
    query = {"_id": ctx.author.id}
    user = collection.find(query)
    for result in user:
        money = result["money"]
    await ctx.send(f"{ctx.author}(id: {ctx.author.id})'s balance is {money}")

#prints shape of context to console
@bot.command()
async def test(ctx):
    print(vars(ctx))









#bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)
bot.run(token=TOKEN)