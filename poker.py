import random
import itertools
from enum import Enum, auto



class PlayerState(Enum):
    SKIP = auto()
    OUT = auto()
    IN = auto()
    TO_CALL = auto()
    ALL_IN = auto()

class HandState(Enum):
    BLINDS = auto()
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN= auto()

class Player():
    def __init__(self, name):
        self.cards = []
        self.stack = 200
        self.name = name
        self.current_bet = 0
        self.state = PlayerState.IN
    
    def fold(self):
        pass
    def check(self):
        pass
    def bet(self):
        pass  
    def get_cards(self) -> list:   
        return self.cards   

class Deck():
    def __init__(self):
        self.cards = []
        self.build()

    def build(self):
        for suit in ['Clubs', 'Spades', 'Diamonds', 'Hearts']:
            for val in ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']:
                self.cards.append(Card(suit, val))

    def deal(self, players):
        for player in players:
            #player.cards.append(self.draw_cards(2))
            player.cards = self.draw_cards(2)

    def shuffle(self):
        for i in range(len(self.cards)-1, 0, -1):
            r = random.randint(0, i)
            self.cards[i], self.cards[r] = self.cards[r], self.cards[i]
    
    def draw_cards(self, amount: int) -> list:
        cards = []
        for i in range(0, amount):
            cards.append(self.cards.pop())
            i += i
        '''
        for card in cards:
            card.show()
        print("==============================================")
        '''
        return cards
    
class Card():
    def __init__(self, suit, val) -> None:
        self.suit = suit
        self.val = val
    
    def show(self):
        print("{} of {}".format(self.val, self.suit))

class Hand():
    def __init__(self, sm_blind: int, big_blind: int, button_loc: int, players: list) -> None:
        self.pot = 0
        self.sm_blind = sm_blind
        self.big_blind = big_blind
        self.button_loc = button_loc
        self.players = players
        self.state_iter = itertools.cycle(HandState)
        self.state = next(self.state_iter)
        self.deck = Deck()
        self.board = []
        self.current_bet = 0
        self.hand_running = True
        self.run_hand()
        

    def run_hand(self):
        for player in self.players:
            if(player.stack > 0):
                player.state = PlayerState.TO_CALL
            else:
                player.state = PlayerState.OUT

        #shuffle and deal cards to players
        self.deck.shuffle()
        self.deck.deal(self.players)

        while(self.hand_running):
            if(self.state == HandState.PREFLOP):
                pass
            elif(self.state == HandState.FLOP):
                self.board = self.deck.draw_cards(3)
            elif(self.state == HandState.TURN):
                self.board.append(self.deck.draw_cards(1)[0])
            elif(self.state == HandState.RIVER):
                self.board.append(self.deck.draw_cards(1)[0])
            elif(self.state == HandState.SHOWDOWN):
                self.find_winner()
                self.reward_pot()
                return
            
            print_board(self.board, self.state)
            self.betting_round()

            if(self.check_winner(self.players)):
                self.reward_pot()
                return
            
            self.state = next(self.state_iter)
            
        

    def betting_round(self):
        for player in self.players:
            if(player.state != PlayerState.OUT):
                player.state = PlayerState.TO_CALL

        in_hand = active_player_iter(self.players)
        player = next(in_hand)

        while(player.state != PlayerState.IN):
            if(self.state == HandState.BLINDS):
                #small blind
                player.current_bet = self.sm_blind
                player.state = PlayerState.TO_CALL
                self.pot += player.current_bet
                self.current_bet = player.current_bet
                print(f"{player.name} posted small blind of {self.current_bet}.")
                print("==============================================")
                player = next(in_hand)

                #big blind
                player.current_bet = self.big_blind
                player.state = PlayerState.IN
                self.pot += player.current_bet
                self.current_bet = player.current_bet
                print(f"{player.name} posted Big Blind of {self.current_bet}.")
                print("==============================================")
                player = next(in_hand)

                self.state = next(self.state_iter)

            if(player.state == PlayerState.TO_CALL):
                print(f"{player.name} it is your turn. Your cards are: ")
                print_cards(player.cards)
                action = int(input(f"The current bet is {self.current_bet}. Call: '1', Raise: '2', or Fold: '3': "))
                if (action == 1):
                    player.current_bet = self.current_bet
                    self.pot += self.current_bet
                    player.state = PlayerState.IN
                    print(f"{player.name} called the bet of {self.current_bet}.")
                    print("==============================================")
                elif ( action == 2):
                    bet = int(input(f"{player.name} enter your bet amount: "))
                    player.current_bet = bet
                    self.pot += bet
                    current_bet = bet

                    #Set IN players to TO_CALL
                    for player_in in self.players:
                        if(player_in.state == PlayerState.IN):
                            player_in.state = PlayerState.TO_CALL
                    
                    player.state = PlayerState.IN
                    print(f"{player.name} raised to {bet}.")
                    print("==============================================")

                elif(action == 3):
                    player.state = PlayerState.OUT
                    print(f"{player.name} folded.")
                    print("==============================================")
                else:
                    print("Please enter 1, 2, or 3!")
            
            player = next(in_hand)
            print(self.state)
        
    
    def check_winner(self, players: list) -> bool:
        count = 0
        for player in players:
            if(player.state == PlayerState.IN):
                count +=1
                if(count > 1):
                    return False
                
        return True

    def find_winner(self):
        pass

    def reward_pot(self):
        pass



def active_player_iter(players: list) -> itertools:
    active_players = []
    for player in players:
        if(player.state != PlayerState.OUT):
            active_players.append(player)

    return itertools.cycle(active_players)

def start_game(player_count: int):
    players = []
    button_loc = 0
    game_running = True
    for player in range(0, player_count):
        players.append(Player(player))

    while(game_running):
        Hand(1, 2, button_loc, players)
        button_loc += 1
        button_loc % player_count
    

def print_cards(cards):
    for card in cards:
        card.show()

def print_board(board, state):
    if(state == HandState.FLOP):
        print("==============================================")
        print(f"The flop is: ")
        print_cards(board)
        print("==============================================")

    elif(state == HandState.TURN):
        print("==============================================")
        print(f"The Turn is: ")
        print_cards(board)
        print("==============================================")

    elif(state == HandState.RIVER):
        print("==============================================")
        print(f"The River is: ")
        print_cards(board)
        print("==============================================")



start_game(3)