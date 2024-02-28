import os
import datetime
import logging
import random

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

class TheButton(discord.ui.View):
    def __init__(self, *, timeout = 10, risk):
        super().__init__(timeout=timeout)
        self.clicked = 0
        self.risk = risk
        self.explosion = 5
        self.last_clicked = None

    async def on_timeout(self) -> None:
        self.stop()
        
        

    @discord.ui.button(label="BUTTON", style=discord.ButtonStyle.red)
    async def the_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if(random.randint(0,100) <= self.explosion):
            button.disabled = True
            await interaction.response.edit_message(content="BOOM!", view=self)
            self.stop()
        else:
            self.clicked += 1
            self.explosion += random.randint(0,5)
            await interaction.response.edit_message(content=f"Button Clicked {self.clicked} Times")
            self.last_clicked = interaction.user
            print(f"Clicked={self.clicked} | explosion={self.explosion} | last_clicked={self.last_clicked.id}")


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
async def selfGive(ctx, value: int):
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

@selfGive.error
async def selfGive_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Command Param must be a integer.")


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
async def give(ctx, user: discord.Member, value: int):
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

@give.error
async def give_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("$give {@user} {value}")


@bot.command()
async def coinflip(ctx, choice: str, amount: int):
    print("COIN FLIP")
    coin = [1, 0]
    if(((choice != "heads") and (choice != "tails")) or (amount < 1)):
        print("BAD CHOICE")
        await ctx.send("Please select heads or tails and an amount greater than 0 to wager")
        await ctx.send("$coinflip {heads || tails} {wager}")
        return
    if(random.choice(coin) == 1):
        print("HEADS")
        await ctx.send("Flipped coin, Heads!")
        if(choice == "heads"):
            await add_balance(ctx.author.id, amount)
            await ctx.send(f"You Won {amount}!")
        else:
            await add_balance(ctx.author.id, (0 - amount))
            await ctx.send(f"You Lost {amount}!")
    else:
        print("TAILS")
        await ctx.send("Flipped coin, Tails!")
        if(choice == "tails"):
            await add_balance(ctx.author.id, amount)
            await ctx.send(f"You Won {amount}!")
        else:
            await add_balance(ctx.author.id, (0 - amount))
            await ctx.send(f"You Lost {amount}!")

@bot.command()
async def button(ctx,value):
    view = TheButton(risk=value)
    msg = await ctx.send("The Button Has Commenced!", view=view)

    timed_out = await view.wait()
    print(view.last_clicked)
    if(timed_out):
        if(view.last_clicked == None):
            await ctx.send("The Button Timed Out\nI guess no one loves the Button :(", view=None)
        else:
            await ctx.send(f"The Button Timed Out\n{view.last_clicked.mention} was the last person to hit the Button!", view=None)
    else:
        await ctx.send(f"The Button Exploded on {view.last_clicked.mention}!\nIt was Clicked {view.clicked} times!", view=None)

    await msg.delete()


@coinflip.error
async def coinflip_error(ctx, error):
    print("ERR")
    print(error)
    if isinstance(error, commands.BadArgument):
        await ctx.send("Please select heads or tails and your amount to wager")
        await ctx.send("$coinflip {heads || tails} {wager}")
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please select heads or tails and your amount to wager")
        await ctx.send("$coinflip {heads || tails} {wager}") 
 
    
@bot.command()
async def roll(ctx, amount: int, faces: int):
    result = []
    for x in range(amount):
        result.append(random.randint(1, faces))
    await ctx.reply(f"You rolled {result} for a total of {sum(result)}")

@roll.error
async def roll_error(ctx, error):
    if isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please enter the amount of dice followed by the type of dice")
        await ctx.send("$roll {amount} {type} \nie. '$roll 2 6' Will roll a 6 sided dice twice.")

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