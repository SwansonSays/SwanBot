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
intents.members = True

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

#Event handling
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

#Greats new user and gives them 1000 coins on server join
@bot.event
async def on_member_join(member):
    id = member.id
    welcome_msg = f"Welcome to the Server {member.name}"
    return_msg = f"Welcome back {member.name}"
    if (not await is_user(id)):
        print(f"Your Starting Balance is $1000!")
        await send_general(welcome_msg)
    else:
        await send_general(return_msg)

#Gives coins for every 30 minutes user is in voice call
@bot.event
async def on_voice_state_update(member, before, after):
    id = member.id
    #Puts Join time into DB when VC is joined
    if before.channel == None and after.channel != None:
        join_time = datetime.datetime.now()

        if(await is_user(id)):
            await set_join_time(id, join_time)
        else:
            await add_user(id)
            print(f"ID:{id} not found. Created new user with starting balance")

    #Pull join_time from DB and calculates money earned for total time in VC
    if before.channel != None and after.channel == None:
        leave_time = datetime.datetime.now()

        if(await is_user(id)):
            join_time = await getJoinTime(id)

            #User earns 50 coins for every half hour they are in VC
            total_seconds = (leave_time - join_time).total_seconds()
            money_earned = int(total_seconds / 1800 * 50)   

            balance = await add_balance(id, money_earned)

            msg = f"{member.name} earned {money_earned} coins for beining in {before.channel}.\nYour new balance is {balance}."
            await send_general(msg)
        else:
            await add_user(id)
            print(f"ID:{id} not found. Created new user with starting balance")



#Command handling
        
#echo response
@bot.command()
async def echo(ctx, *args):
    if(len(args) > 0):
        arguments = ' '.join(args)
        await ctx.send(arguments)
    else:
        await ctx.send("Echo must be followed by at least one character.")

#Greats user who send command
@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author}!')

#Give money to anyone. In future admin use only or helper function only
@bot.command()
async def selfGive(ctx, value):
    value = int(value)
    id = ctx.author.id

    if(await is_user(id)):
        if value > 0:
            money = await add_balance(id, value)
            print(f"{value} given to {ctx.author}(id: {ctx.author.id}")
            print(f"{ctx.author}'s new balance is {money}")
            await ctx.send(f"{ctx.author}'s new balance is {money}")
        else:
            await ctx.send(f"{value} is not a valid value. Please try again")
    else :
        await add_user(id)
        print(f"ID:{id} not found. Created new user with starting balance")


#Sends balance of message author or tagged user
@bot.command()
async def balance(ctx):
    if(len(ctx.message.mentions) > 0):
        balance = await get_balance(ctx.message.mentions[0].id)
        await ctx.send(f"{ctx.message.mentions[0].name}(id: {ctx.message.mentions[0].id})'s balance is {balance}")
    else:
        balance = await get_balance(ctx.author.id)
        await ctx.send(f"{ctx.author}(id: {ctx.author.id})'s balance is {balance}")

#send user value
@bot.command()
async def give(ctx, user, value):
    if(len(ctx.message.mentions) >= 0):
        sender = ctx.author.id
        recipient = ctx.message.mentions[0].id
        value = int(value)

        balance = await get_balance(sender)
        if(balance > value):
            await add_balance(recipient, value)
            await add_balance(sender, (0 - value))
            await ctx.send(f"{ctx.author.name} sent {ctx.message.mentions[0].name} {value}")
        else:
            await ctx.send(f"Your balance of {balance} is smaller then the amount({value}) you want to send")
    else:
        await ctx.send("Must tag user to send money to")

@bot.command()
async def addAll(ctx):
    for guild in bot.guilds:
        for member in guild.members:
            if(not await is_user(member.id)):
                await add_user(member.id)
                print(f"{member}(id:{member.id}) was added to user list")


#prints shape of context to console
@bot.command()
async def test(ctx):
    print(vars(ctx))


#DB API

async def add_balance(id, value):
    balance = await get_balance(id)
    new_balance = balance + value
    await set_balance(id, new_balance)
    return new_balance

async def get_balance(id):
    user = await get_user(id)
    for result in user:
        balance = result["money"]
    return balance

async def set_balance(id, balance):
    collection.update_one({"_id": id}, {"$set":{"money": balance}})


async def add_user(id):
    myquery = {"_id": id}
    if(not await is_user(id)):
        post = {"_id": id, "money": 1000, "join_time": 0}
        collection.insert_one(post)
        return True
    print(f"{id} is already in database")
    return False

async def is_user(id):
    query = {"_id": id}
    if(collection.count_documents(query) == 0):
        return False
    return True

async def get_user(id):
    query = {"_id": id}
    user = collection.find(query)
    return user

async def set_join_time(id, join_time):
    collection.update_one({"_id": id}, {"$set":{"join_time": join_time}})

async def getJoinTime(id):
    user = await get_user(id)
    for result in user:
        join_time = result["join_time"]
    return join_time



# Helper Funcs
async def send_general(msg):
    channel = bot.get_channel(784337067307302914) #hard coded general channel
    await channel.send(msg)



#bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)
bot.run(token=TOKEN)