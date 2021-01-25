#!/usr/bin/env python3.8

import asyncio
import json
import random
import time
import traceback
import websockets

import structures.book as book
import util.helpers as util

class MatchingEngine:
    def __init__(self):
        util.print_core('Initialising...')
        self._connected_users = set()       # A set of all the connected websocket clients
        self._lobby = Lobby()               # Lobby of the rooms
        self._q = asyncio.Queue()


    async def send_rooms(self, ws):
        await ws.send(json.dumps({
            'type' : 'RoomUpdate',
            'data' : self._lobby.get_rooms()
        }))

    async def send_players(self, ws):
        await ws.send(json.dumps({
            'type' : 'PlayerUpdate',
            'data' : self._lobby.get_players()
        }))

    async def client_handler(self, websocket, path):
        self._connected_users.add(websocket)
        print('-' * 60)
        util.print_core('A client has connected!')
        await self.send_rooms(websocket)
        await self.send_players(websocket)
        print('-' * 60)
        try:
            async for _ in websocket:
                message = await websocket.recv()
                d = json.loads(message)
                await self._q.put((d, websocket))
                
        except Exception:
            traceback.print_exc()
            util.print_core('Client unexpectedly disconnected!')
            self._connected_users.remove(websocket)

    async def consume(self, q: asyncio.Queue):
        while True:
            msg, ws = await self._q.get()
            if isinstance(msg, dict):
                await self.update_and_send_response(msg, ws)

            elif isinstance(msg, list):
                for m in msg:
                    await self.update_and_send_response(m, ws)
            
            else:
                util.print_core('Unknown message datatype')

    async def update_and_send_response(self, msg, ws):
        if isinstance(msg, dict):
            msg_json = msg
            msg = json.dumps(msg)
        elif isinstance(msg, str):
            msg_json = json.loads(msg)

        if 'type' not in msg_json.keys():
            print('Uncaught message! No type!')
            return
        else:
            msg_type = msg_json['type']

        response  = []
        if msg_type == 'NewRoom':
            if self._lobby.new_room(msg_json['data']['name']):
                response = [
                    {
                        'type' : 'Info',
                        'status' : 'New room successfully created'
                    },
                    {
                        'type' : 'RoomUpdate',
                        'data' : self._lobby.get_rooms()
                    }
                ]
            else:
                response = {
                    'type' : 'Info',
                    'status' : 'Failed to create new room - duplicate name'
                }
        elif msg_type == 'DeleteRoom':
            if self._lobby.delete_room(msg_json['data']['name']):
                response = [
                    {
                        'type' : 'Info',
                        'status' : 'Deleted room'
                    },
                    {
                        'type' : 'RoomUpdate',
                        'data' : self._lobby.get_rooms()
                    }
                ]
            else:
                response = {
                    'type' : 'Info',
                    'status' : 'Failed to delete room - does not exist.'
                }
        elif msg_type == 'NewPlayer':
            c = await self._lobby.new_player(msg_json['data']['name'], ws)
            if c:
                response = [
                    {
                        'type' : 'Info',
                        'status' : 'New player successfully joined game'
                    },
                    {
                        'type' : 'PlayerUpdate',
                        'data' : self._lobby.get_players()
                    }
                ]
            else:
                response = {
                    'type' : 'Info',
                    'status' : 'Failed to create new player - duplicate name'
                }
        elif msg_type == 'DeletePlayer':
            if self._lobby.delete_player(msg_json['data']['name']):
                response = [
                    {
                        'type' : 'Info',
                        'status' : 'Deleted player'
                    },
                    {
                        'type' : 'PlayerUpdate',
                        'data' : self._lobby.get_players()
                    }
                ]
            else:
                response = {
                    'type' : 'Info',
                    'status' : 'Failed to delete player - does not exist.'
                }

        elif msg_type == 'JoinRoom':
            player = msg_json['data']['player']
            room = msg_json['data']['room']
            c1 = await self._lobby.get_player(player).join_room(room)
            c2 = await self._lobby.get_room(room).join(self._lobby.get_player(player))
            if (c1 and c2):
                response = {
                    'type' : 'Info',
                    'status' : f'{player} has joined {room}'
                }
            else:
                response = {
                    'type' : 'Info',
                    'status' : f'{player} failed to join {room}'
                }
        elif msg_type == 'LeaveRoom':
            player = msg_json['data']['player']
            room = msg_json['data']['room']
            if (
                self._lobby.get_player(player).leave_room(room) and
                self._lobby.get_room(room).leave(player)
            ):
                response = {
                    'type' : 'Info',
                    'status' : f'{player} has left {room}'
                }
            else:
                response = {
                    'type' : 'Info',
                    'status' : f'{player} failed to leave {room}'
                }
        elif msg_type == 'StartGame':
            room = self._lobby.get_room(msg_json['data']['room'])
            await room.start_game()

        elif msg_type == 'RevealCard':
            room = self._lobby.get_room(msg_json['data']['room'])
            player = msg_json['data']['player']
            card = tuple(msg_json['data']['card'])
            await room.reveal_card(player, card)

        elif msg_type == 'NewInstrument':
            room = self._lobby.get_room(msg_json['data']['room'])
            i_type = msg_json['data']['type']
            if i_type == 'underlying':
                await room.init_underlying()
            else:
                await room.new_option(
                    msg_json['data']['name'], 
                    msg_json['data']['type'],
                    msg_json['data']['strike']
                )

        elif msg_type == 'NewOrder':
            room = self._lobby.get_room(msg_json['data']['room'])
            player_name = msg_json['data']['player']
            instrument = msg_json['data']['instrument']
            price = msg_json['data']['price']
            size = msg_json['data']['size']
            direction = msg_json['data']['direction']
            await room.new_order(instrument, player_name, price, size, direction)
        elif msg_type == 'CancelOrder':
            room = self._lobby.get_room(msg_json['data']['room'])
            player_name = msg_json['data']['player']
            instrument = msg_json['data']['instrument']
            direction = msg_json['data']['direction']
            price = msg_json['data']['price']
            await room.cancel_order(instrument, player_name, int(price), direction)
        else:
            print(json.dumps(msg_json, indent=4))
            

        await self.broadcast(response)

    async def broadcast(self, msg):
        if isinstance(msg, list):
            for m in msg:
                await self.broadcast(m)
        elif isinstance(msg, str):
            await self.broadcast(msg)
        elif isinstance(msg, dict):
            for ws in self._connected_users.copy():
                try:
                    await ws.send(json.dumps(msg))
                except:
                    if ws in self._connected_users:
                        self._connected_users.discard(ws)
                        # util.print_core('Could not send, removing ws')
                    else:
                        pass

    async def run(self, port='8887'):
        util.print_core(f'Starting server on port {port}')
        await websockets.server.serve(self.client_handler, 'localhost', port)

        consumer = asyncio.create_task(self.consume(self._q))
        await asyncio.gather(consumer)

async def main(port='8887'):
    server = MatchingEngine()
    await server.run(port=port)

class Lobby:
    def __init__(self):
        self._rooms = {}
        self._players = {}

    def new_room(self, name):
        if name in self._rooms.keys():
            util.print_core('Room already exists')
            return 0
        else:
            util.print_core('Making a new room')
            self._rooms[name] = Room(name)
            return 1

    def delete_room(self, name):
        if name in self._rooms.keys():
            del self._rooms[name]
            return 1
        else:
            return 0

    async def new_player(self, player_name, ws):
        if player_name in self._players.keys():
            util.print_core('Player already exists')
            return 0
        else:
            util.print_core(f'Creating player: {player_name}')
            self._players[player_name] = Player(player_name, ws)
            await self._players[player_name].send_message(
                {
                    'type' : 'PlayerDetails',
                    'data' : player_name
                }
            )
            return 1

    def delete_player(self, player_name):
        if player_name in self._players.keys():
            del self._players[player_name]
            return 1
        else:
            return 0

    def get_rooms(self):
        return sorted(list(self._rooms.keys()))

    def get_players(self):
        return sorted(list(self._players.keys()))

    def get_player(self, player):
        return self._players[player]
        
    def get_room(self, room):
        return self._rooms[room]

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._players[key]

class Player:
    def __init__(self, name, ws):
        self._player_name = name
        self._ws = ws
        self._player_id = util.hash_string(name)
        self._rooms = set()

        self._cards = {}                    # Dictionary of cards for each room
        self._positions = {}                # Dictionary of positions for each room
        self._orders = {}                   # Dictionary of orders for each room

    async def join_room(self, room_name):
        if room_name in self._rooms:
            util.print_core(f'{self._player_name} is already in {room_name}')
            return 0
        else:
            self._rooms.add(room_name)

            self._orders[room_name] = {}
            self._positions[room_name] = {}
            self._cards[room_name] = []

            await self.send_message({
                'type' : 'CurrentRoom',
                'data' : {
                    'name' : room_name
                }
            })
            util.print_core(f'{self._player_name} has joined {room_name}')
            return 1

    def leave_room(self, room_name):
        if room_name in self._rooms:
            self._rooms.remove(room_name)
            del self._orders[room_name]
            del self._positions[room_name]
            util.print_core(f'{self._player_name} has left {room_name}')
            return 1
        return 0

    async def send_message(self, msg):
        try:
            if isinstance(msg, str):
                await self._ws.send(msg)
            elif isinstance(msg, list):
                for m in msg:
                    await self._ws.send(m)
            else:
                await self._ws.send(json.dumps(msg))
        except:
            util.print_core('Could not send!')

    def receive_card(self, room, card):
        self._cards[room].append(card)

    def get_cards(self, room):
        return self._cards[room]

class CardDeck:
    def __init__(self):
        util.print_core('Making new deck of cards')
        self._remaining_cards = []
        for i in range(1, 14):
            for suit in ['S', 'H', 'C', 'D']:
                self._remaining_cards.append((i, suit))
    
    def deal(self):
        random.shuffle(self._remaining_cards)
        return self._remaining_cards.pop()

class Room:
    def __init__(self, name):
        self._name = name                   # Name of the room
        self._status = 'waiting'
        self._players = {}                  # Members of the room

        self._instruments = []              # Instruments
        self._books = {}                    # A book of open orders for each instrument
        self._trades = {}                   # A list of trades for each user
        self._positions = {}
        
        self._cards = CardDeck()
        self._revealed_cards = {}
        self._n_cards = 3

        self._settlement_value = None

        self._underlying = {}
        self._options = {}
    
    async def tell_room(self, msg):
        for _, player in self._players.items():
            try:
                await player.send_message(json.dumps(msg))
            except:
                util.print_core('Could not send!')
            

    async def join(self, player: Player):
        person_name = player._player_name
        if self._status != 'waiting' and person_name not in self._players.keys():
            return 0
        if person_name in self._players.keys():
            util.print_core(f'{person_name} is already in {self._name}')
            await player.send_message({
                'type' : 'RoomPlayersUpdate',
                'data' : {
                    'room' : self._name,
                    'players' : list(self._players.keys())
                }
            })
            await player.send_message({
                'type' : 'GameStart',
                'data' : {
                    'cards' : player.get_cards(self._name)
                }
            })
            return 0
        else:
            self._players[person_name] = player
            util.print_core(f'{person_name} has joined {self._name}')
            await self.tell_room({
                'type' : 'RoomPlayersUpdate',
                'data' : {
                    'room' : self._name,
                    'players' : list(self._players.keys())
                }
            })
            return 1

    def leave(self, person_name):
        if person_name in self._players.keys():
            del self._players[person_name]
            util.print_core(f'{person_name} has left {self._name}')
            return 1
        else:
            return 0

    async def update_positions(self, player_name, instrument_name, price, size, ask_bid):
        util.print_core(f'Updating positions for {player_name}')
        prev_size = self._positions[player_name][instrument_name]['size']
        prev_average = self._positions[player_name][instrument_name]['average_price']
        if ask_bid == 'bid':
            self._positions[player_name][instrument_name]['size'] += size
            if size + prev_size == 0:
                self._positions[player_name][instrument_name]['average_price'] = 0
            else:
                self._positions[player_name][instrument_name]['average_price'] = ((prev_size * prev_average) + (size * price)) / (size + prev_size)
        elif ask_bid == 'ask':
            self._positions[player_name][instrument_name]['size'] -= size
            if prev_size - size == 0:
                self._positions[player_name][instrument_name]['average_price'] = 0
            else:
                self._positions[player_name][instrument_name]['average_price'] = ((prev_size * prev_average) - (size * price)) / (prev_size - size)
        else:
            util.print_core('Something bad happened!')

        await self.send_positions(specific_player=player_name)

    async def new_trade(self, instrument_name, price, size, direction):
        self._trades[instrument_name].append({
            'price' : price,
            'size' : size,
            'direction' : direction,
            'instrument' : instrument_name,
            'timestamp' : time.time()
        })
        await self.send_trades()

    async def start_game(self):
        if self._status == 'started':
            util.print_core(f'The game in {self._name} has already started!')
            await self.tell_room({
                'type': 'Info', 'status' : f'The game in room {self._name} has already started'
            })
            return
            
        util.print_core(f'The game in {self._name} is starting!')
        await self.tell_room({
            'type': 'Info', 'status' : f'The game in room {self._name} has begun'
        })
        settlement_value = 0
        for player_name, player in self._players.items():
            for _ in range(self._n_cards):
                card = self._cards.deal()
                player.receive_card(self._name, card)
                settlement_value += card[0]

            await player.send_message({
                'type' : 'GameStart',
                'data' : {
                    'cards' : player.get_cards(self._name)
                }
            })

            self._positions[player_name] = {}
        
        self._settlement_value = settlement_value
        self._status = 'started'
        util.print_core(f'The game has initialised with settlement value {settlement_value}!')
        await self.init_underlying()

    async def reveal_card(self, player_name, card):
        if player_name in self._revealed_cards.keys():
            if card not in self._revealed_cards[player_name]:
                self._revealed_cards[player_name].append(card)
        else:
            self._revealed_cards[player_name] = [card]
        await self.tell_room({
            'type' : 'RevealedCards',
            'data' : self._revealed_cards,
        })
        util.print_core(f'Revealing cards {self._revealed_cards}')

    async def init_underlying(self):
        name = 'SUM-UNDERLYING'
        util.print_core(f'The instrument, {name} has been initialised!')
        self._underlying = {
            'type' : 'underlying',
            'settlement_price' : self._settlement_value,
            'last_price' : None
        }
        self._instruments.append(name)
        self._books[name] = book.OrderBook(name, 1)
        await self.send_instruments()
        for player_name in self._players.keys():
            self._positions[player_name][name] = {
                'size' : 0,
                'average_price' : 0,
            }
            self._trades[name] = []
        await self.send_positions()

    async def new_option(self, name, option_type, strike):
        if strike is not None and strike > 0:
            if name not in self._instruments:
                util.print_core(f'The option, {name} has been initialised!')
                self._options[name] = {
                    'type' : option_type,
                    'settlement_price' : strike,
                    'last_price' : None,
                }
                self._instruments.append(name)
                self._books[name] = book.OrderBook(name, 1)
                await self.send_instruments()
                for player_name in self._players.keys():
                    self._positions[player_name][name] = {
                        'size' : 0,
                        'average_price' : 0,
                    }
                    self._trades[name] = []

                await self.send_positions()
            else:
                util.print_core(f'Could not initialise option (already exists)!')
                await self.tell_room({
                    'type' : 'Info',
                    'status' : 'Unable to create option'
                })

        else:
            util.print_core(f'Could not initialise option (likely None type)!')
            await self.tell_room({
                'type' : 'Info',
                'status' : 'Unable to create option'
            })

    async def new_order(self, instrument_name, player_name, price, size, direction):
        if price is None or size is None or direction is None:
            await self.tell_room({'type': 'Info', 'status' : 'Invalid order params'})
            return
        util.print_core(f'Sending new order to the book for {instrument_name}')
        book = self._books[instrument_name]
        await book.new_order({
            'room' : self,
            'player' : self._players[player_name],
            'price' : price,
            'size' : size,
            'direction' : direction,
            'instrument' : instrument_name
        })
        await self.send_books()
        
    async def cancel_order(self, instrument_name, player_name, price, direction):
        book = self._books[instrument_name]
        await book.cancel_order(player_name, price, direction)
        await self.send_books()


    async def send_instruments(self):
        await self.tell_room({
            'type' : 'InstrumentsUpdate',
            'data' : self._instruments
        })

    async def send_positions(self, specific_player=None):
        if specific_player is None:
            for player_name, player in self._players.items():
                await player.send_message({
                    'type' : 'PositionUpdate',
                    'data' : self._positions[player_name]
                })
        else:
            player = self._players[specific_player]
            await player.send_message({
                'type' : 'PositionUpdate',
                'data' : self._positions[specific_player]
            })

    async def send_books(self):
        for _, book in self._books.items():
            await self.tell_room(book.as_update())

    async def send_trades(self):
        await self.tell_room({
            'type' : 'Trade',
            'data' : self._trades
        })

    def __hash__(self):
        return util.hash_string(self._name)

    def __eq__(self, r):
        if self.__hash__() == r.__hash__():
            return True
        else:
            return False
            
    def __ne__(self, r):
        return (not self.__eq__(r))
