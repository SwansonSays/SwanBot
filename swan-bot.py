import datetime
import logging
import random
import asyncio
import itertools

import discord
from discord.ext import commands

from database import DataBase
import settings

logger = settings.logging.getLogger("bot")

def run():
    #TODO figure out how to send err's to console but debug statements to log
    #handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    db = DataBase()

    bot = commands.Bot(command_prefix='$', intents=intents)


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
            roll = random.randint(0,100)
            if(roll <= self.explosion):
                self.clicked += 1
                button.disabled = True
                await interaction.response.edit_message(content="BOOM!", view=self)
                self.stop()
            else:
                self.clicked += 1
                self.explosion += random.randint(0,5)
                await interaction.response.edit_message(content=f"Button Clicked {self.clicked} Times")
                self.last_clicked = interaction.user
                
            print(f"Clicked={self.clicked} | explosion={self.explosion} | roll={roll} | last_clicked={self.last_clicked.id}")

    ##################
    # Event Handling #
    ##################        

    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")
        print(f'We have logged in as {bot.user}')


    #Greats new user and gives them 1000 coins on server join
    @bot.event
    async def on_member_join(member):
        id = member.id
        welcome_msg = f"Welcome to the Server {member.name}"
        return_msg = f"Welcome back {member.name}"
        if (not await db.is_user(id)):
            await db.add_user(id)
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

            if(await db.is_user(id)):
                await db.set_join_time(id, join_time)
            else:
                await db.add_user(id)
                print(f"ID:{id} not found. Created new user with starting balance")

        #Pull join_time from DB and calculates money earned for total time in VC
        if before.channel != None and after.channel == None:
            leave_time = datetime.datetime.now()

            if(await db.is_user(id)):
                join_time = await db.getJoinTime(id)

                #User earns 50 coins for every half hour they are in VC
                total_seconds = (leave_time - join_time).total_seconds()
                money_earned = int(total_seconds / 1800 * 50)   

                balance = await db.add_balance(id, money_earned)

                msg = f"{member.name} earned {money_earned} coins for beining in {before.channel}.\nYour new balance is {balance}."
                await send_general(msg)
            else:
                await db.add_user(id)
                print(f"ID:{id} not found. Created new user with starting balance")


    ####################
    # Command Handling #
    ####################      


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
        await ctx.send(f'Hello {ctx.author.mention}!')


    #Give money to anyone. In future admin use only or helper function only
    @bot.command(
        hidden=True
    )
    async def selfGive(ctx, value: int):
        id = ctx.author.id

        if(await db.is_user(id)):
            if value > 0:
                money = await db.add_balance(id, value)
                print(f"{value} given to {ctx.author}(id: {ctx.author.id}")
                print(f"{ctx.author}'s new balance is {money}")
                await ctx.send(f"{ctx.author}'s new balance is {money}")
            else:
                await ctx.send(f"{value} is not a valid value. Please try again")
        else :
            await db.add_user(id)
            print(f"ID:{id} not found. Created new user with starting balance")


    #Sends balance of message author or tagged user
    @bot.command()
    async def balance(ctx):
        if(len(ctx.message.mentions) > 0):
            balance = await db.get_balance(ctx.message.mentions[0].id)
            await ctx.send(f"{ctx.message.mentions[0].name}(id: {ctx.message.mentions[0].id})'s balance is {balance}")
        else:
            balance = await db.get_balance(ctx.author.id)
            await ctx.send(f"{ctx.author}(id: {ctx.author.id})'s balance is {balance}")


    #send user value
    @bot.command()
    async def give(ctx, user: discord.Member, value: int):
        if(len(ctx.message.mentions) >= 0):
            sender = ctx.author.id
            recipient = ctx.message.mentions[0].id
            value = int(value)

            balance = await db.get_balance(sender)
            if(balance > value):
                await db.add_balance(recipient, value)
                await db.add_balance(sender, (0 - value))
                await ctx.send(f"{ctx.author.name} sent {ctx.message.mentions[0].name} {value}")
            else:
                await ctx.send(f"Your balance of {balance} is smaller then the amount({value}) you want to send")
        else:
            await ctx.send("Must tag user to send money to")


    @bot.command(
        aliases=['coin', 'flip', 'cf']
    )
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
                await db.add_balance(ctx.author.id, amount)
                await ctx.send(f"You Won {amount}!")
            else:
                await db.add_balance(ctx.author.id, (0 - amount))
                await ctx.send(f"You Lost {amount}!")
        else:
            print("TAILS")
            await ctx.send("Flipped coin, Tails!")
            if(choice == "tails"):
                await db.add_balance(ctx.author.id, amount)
                await ctx.send(f"You Won {amount}!")
            else:
                await db.add_balance(ctx.author.id, (0 - amount))
                await ctx.send(f"You Lost {amount}!")

    @bot.command()
    async def button(ctx,value):
        view = TheButton(risk=value)
        msg = await ctx.send("The Button Has Commenced!", view=view)

        timed_out = await view.wait()
        if(timed_out):
            if(view.last_clicked == None):
                await ctx.send("The Button Timed Out\nI guess no one loves the Button :(", view=None)
            else:
                await ctx.send(f"The Button Timed Out\n{view.last_clicked.mention} was the last person to hit the Button!", view=None)
        else:
            await ctx.send(f"The Button Exploded on {view.last_clicked.mention}!\nIt was Clicked {view.clicked} times!", view=None)

        await msg.delete()


    @bot.command()
    async def roll(ctx, amount: int, faces: int):
        result = []
        for x in range(amount):
            result.append(random.randint(1, faces))
        await ctx.reply(f"You rolled {result} for a total of {sum(result)}")


    @bot.command(
        hidden=True
    )
    async def addAll(ctx):
        for guild in bot.guilds:
            for member in guild.members:
                if(not await db.is_user(member.id)):
                    await db.add_user(member.id)
                    print(f"{member}(id:{member.id}) was added to user list")


    #prints shape of context to console
    @bot.command()
    async def test(ctx):
        print(vars(ctx))

    @bot.command(
        aliases=['dd'],
        help="$devildice {wager: int}",
        description="Player 1 rolls a d8. The player following rolls a dice with whatever " +
        "number the previous player rolls as the amount of faces on their die. This continues " +
        "untill someone rolls a 1. The player that did not roll the one wins the other players wager",
        brief="| Gambling Dice Game",
    )
    async def devildice(ctx, bet: int = commands.parameter(description="The amount to wager.")):
        await ctx.send(f"{ctx.author.mention} has started a game of Devil Dice. Enter 'join' or 'j' to join.")

        def check(m):
            return m.author != ctx.author and m.channel == ctx.channel
        
        def turn_check(m):
            if(m.author != player or m.channel != ctx.channel):
                print("Wrong other or channel")
                return False
            elif(m.author == player and m.content.lower() != "roll"):
                print("Right author wrong cmd")
                return False
            else:
                print("lets go")
                return True


        try:
            response = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No one joined in time. Please try again.")
            return
        
        if response.content.lower() not in ("join", "j"):
            return
        
        game_running = True
        die = 8
        
        players = itertools.cycle([ctx.author, response.author])
        
        player = next(players)

        while game_running:
            await ctx.send(f"{player.mention} It is your turn. Type roll to go.")

            try:
                turn = await bot.wait_for('message', check=turn_check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send("Player did not respond in time. Match forfieted.")
                return

            die = random.randint(1, die)
            await ctx.send(f"{player.mention} rolled a {die}.")
            if(die == 1):
                loser = player
                winner = next(players)
                await ctx.send(f"{winner.mention} you win {bet}")
                await db.add_balance(winner.id, bet)
                await db.add_balance(loser.id, (0 - bet))
                return

            
            player = next(players)





    @bot.command(
        aliases=['e'],
        help="This is help",
        description="This is description",
        brief="This is brief",
        enabled=True,
        hidden=False
    )
    async def example(ctx):
        ''' Only shows if description or nothing. Replaces help if nor help in help $example '''
        await ctx.send("This is the command example")

        return

    @example.before_invoke
    async def before_invoke_example(ctx):
        await ctx.send("This is a before invoke decorator")

    @example.after_invoke
    async def after_invoke_example(ctx):
        await ctx.send("This is a after invoke decorator")



    ###################
    # Error Handleing #
    ###################
    @selfGive.error
    async def selfGive_error(ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("Command Param must be a integer.")


    @give.error
    async def give_error(ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("$give {@user} {value}")

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


    @roll.error
    async def roll_error(ctx, error):
        if isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please enter the amount of dice followed by the type of dice")
            await ctx.send("$roll {amount} {type} \nie. '$roll 2 6' Will roll a 6 sided dice twice.")


    ################
    # Helper Funcs #
    ################

    async def send_general(msg):
        channel = bot.get_channel(784337067307302914) #hard coded general channel
        await channel.send(msg)



    #bot.run(token=TOKEN, log_handler=handler, log_level=logging.DEBUG)
    bot.run(token=settings.TOKEN, root_logger=True)

if __name__ == "__main__":
    run()