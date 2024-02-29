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
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    db = DataBase()

    bot = commands.Bot(command_prefix='$', intents=intents)

    class TheButton(discord.ui.View):
        def __init__(self, *, timeout = 10, wager):
            super().__init__(timeout=timeout)
            self.clicked = 0
            self.wager = wager
            self.explosion = 5
            self.last_clicked = None

        async def on_timeout(self) -> None:
            self.stop()
            
            

        @discord.ui.button(label="BUTTON", style=discord.ButtonStyle.red)
        async def the_button(self, interaction: discord.Interaction, button: discord.ui.Button):

            if not await check_balance(interaction.user.id, self.wager):
                await interaction.response.send_message("You do not have the balance required to wager that amount.")
                return
            await collect_wager(interaction.user.id, self.wager)
            
            roll = random.randint(0,100)
            if(roll <= self.explosion):
                self.clicked += 1
                button.disabled = True
                await interaction.response.edit_message(content="BOOM!", view=self)
                await pay_winner(self.last_clicked.id, self.wager, self.clicked)
                self.stop()
            else:
                self.clicked += 1
                self.explosion += random.randint(0,5)
                await interaction.response.edit_message(content=f"Button Clicked {self.clicked} Times. Pot: {self.wager * self.clicked}. Click costs {self.wager}.")
                self.last_clicked = interaction.user
                
            print(f"Clicked={self.clicked} | explosion={self.explosion} | roll={roll} | last_clicked={self.last_clicked.id}")

    ##################
    # Event Handling #
    ##################        
    @bot.event
    async def on_ready():
        logger.info(f"User: {bot.user} (ID: {bot.user.id})")
        print(f'We have logged in as {bot.user}')
        await send_general("Ready to rock and roll!")


    @bot.event
    async def on_member_join(member):
        '''
        Adds new users to database with starting balance and greets them
        '''
        id = member.id
        welcome_msg = f"Welcome to the Server {member.name}"
        return_msg = f"Welcome back {member.name}"
        if (not await db.is_user(id)):
            await db.add_user(id)
            print(f"Your Starting Balance is $1000!")
            await send_general(welcome_msg)
        else:
            await send_general(return_msg)


    @bot.event
    async def on_voice_state_update(member, before, after):
        '''
        Awards money to user for time spent in voice call
        '''
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
    @bot.command()
    async def echo(ctx, *args):
        '''
        Bot responds with whatever follows echo
        Args:
            args: Message to be echo'd
        '''
        if(len(args) > 0):
            arguments = ' '.join(args)
            await ctx.send(arguments)
        else:
            await ctx.send("Echo must be followed by at least one character.")


    @bot.command()
    async def hello(ctx):
        '''
        Bot greets user
        '''
        await ctx.send(f'Hello {ctx.author.mention}!')


    @bot.command(
        hidden=True
    )
    async def selfGive(ctx, value: int):
        '''
        Admin Command to increase balance for testing purposes
        Args:
            value (int): Amount of money to increase balance by
        '''
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


    @bot.command()
    async def balance(ctx):
        '''
        Check your own balance or balance of tagged user
        '''
        if(len(ctx.message.mentions) > 0):
            balance = await db.get_balance(ctx.message.mentions[0].id)
            await ctx.send(f"{ctx.message.mentions[0].name}(id: {ctx.message.mentions[0].id})'s balance is {balance}")
        else:
            balance = await db.get_balance(ctx.author.id)
            await ctx.send(f"{ctx.author}(id: {ctx.author.id})'s balance is {balance}")


    @bot.command()
    async def give(ctx, user: discord.Member, value: int):
        '''
        Send a amount of money from your balance to another user
        Args:
            user (discord.Member): User to send money to
            value (int): amount to send
        '''
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
    async def coinflip(ctx, choice: str, wager: int):
        '''
        Flip a coin and if it lands on what your 
        choice recieve double your wager
        Args:
            choice (str): Choice of heads or tails.
            wager (int): Amount to wager.
        '''
        id = ctx.author.id
        choice = choice.lower()

        # Returns if invalid choice or wager
        if(((choice != "heads") and (choice != "tails")) or (wager < 1)):
            await ctx.reply("*Please select heads or tails and an amount greater than 0 to wager")
            await ctx.reply("*$coinflip {heads | tails} {wager}")
            return

        if not await check_balance(id, wager):
            await ctx.reply("You do not have the balance required to wager that amount.")
            return
        
        await collect_wager(id, wager)

        coin = ["Heads", "Tails"]
        result = random.choice(coin)
        if(result == "Heads" and choice == "heads") or (result == "Tails" and choice == "tails"):
            await ctx.reply(f"Flipped coin, {result}!\nYou Won {wager}! Your balance is now {await pay_winner(id, wager, 2)}")
        else:
            await ctx.reply(f"Flipped coin, {result}!\nYou Lost {wager}! Your balance is now {await db.get_balance(id)}")


    @bot.command()
    async def button(ctx, wager: int):
        '''
        Button gambling game. Work in Progress
        Args:
            wager (int): Amount to wager
        '''
        if not await check_balance(ctx.author.id, wager):
            await ctx.reply("You do not have the balance required to wager that amount.")
            return

        view = TheButton(wager=wager)
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
        '''
        Roll a specified amount of dice with a specified amount of faces
        Args:
            amount (int): Amount of dice to roll
            faces (int): Amount of faces on each die
        '''
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


    @bot.command()
    async def test(ctx):
        '''
        Print shape of ctx for testing purposes
        '''
        print(vars(ctx))


    @bot.command(
        aliases=['dd'],
        help="$devildice {wager: int}",
        description="Player 1 rolls a d8. The player following rolls a dice with whatever " +
        "number the previous player rolls as the amount of faces on their die. This continues " +
        "untill someone rolls a 1. The player that did not roll the one wins the other players wager",
        brief="| Gambling Dice Game",
    )
    async def devildice(ctx, wager: int):
        '''
        Dice game where players roll increasingly smaller die untill somone rolls a 1 and loses
        Args:
            wager (int): Amount to wager.
        '''
        if not await check_balance(ctx.author.id, wager):
            await ctx.reply("You do not have the balance required to wager that amount.")
            return
        
        await ctx.send(f"{ctx.author.mention} has started a game of Devil Dice. Enter 'join' or 'j' to join.")

        async def check(m):
            return m.author != ctx.author and m.channel == ctx.channel and await check_balance(m.author, wager)
        
        def turn_check(m):
            if(m.author != player or m.channel != ctx.channel):
                return False
            elif(m.author == player and m.content.lower() != "roll"):
                return False
            else:
                return True


        try:
            response = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No one joined in time. Please try again.")
            return
        
        if response.content.lower() not in ("join", "j"):
            return
        
        await collect_wager(ctx.author.id, wager)
        await collect_wager(response.author.id, wager)
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
                winner = next(players)
                await ctx.send(f"{winner.mention} you win {wager}.\nYour balance is {await pay_winner(winner.id, wager * 2)}")
                return

            
            player = next(players)


    @bot.command(
        aliases=['russian-roulette', 'rr'],
        enabled=False
    )
    async def russianroulette(ctx, wager: int):
        if not await check_balance(ctx.author.id, wager):
            await ctx.reply("You do not have the balance required to wager that amount.")
            return
        
        await ctx.send(f"{ctx.author.mention} has started a game of Russian Roulette. Enter 'join' or 'j' to join.")

        async def check(m):
            return m.author != ctx.author and m.channel == ctx.channel and await check_balance(m.author, wager)

        try:
            response = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("No one joined in time. Please try again.")
            return
        
        if response.content.lower() not in ("join", "j"):
            return
        

        
        
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
        if isinstance(error, commands.BadArgument) or isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("!Please select heads or tails and your amount to wager")
            await ctx.send("!$coinflip {heads || tails} {wager}") 


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

    async def check_balance(id, wager: int) -> bool:
        '''
        Confirmers player with id has enough balance to wager
        Args:
            id: User id
            wager (int): Amount to wager.
        Returns:
            bool: Whether user has enough balance or not
        '''
        return (await db.get_balance(id) > wager)
    
    async def collect_wager(id, wager: int) -> None:
        '''
        Collects wager from player. Must check that player has enough balance first.
        Args:
            id: User id
            wager (int): Amount to take from balance
        '''
        await db.add_balance(id, 0 - wager)

    async def pay_winner(id, wager: int, multiplier: int) -> int:
        '''
        Add multiplier * wager to players balance
        Args:
            id: User id
            wager (int): Amount to pay out
            multiplier (int): Amount to multiply wager by
        Returns: New balance of winner
        '''       
        return await db.add_balance(id, wager * multiplier)


    bot.run(token=settings.TOKEN, root_logger=True)

if __name__ == "__main__":
    run()