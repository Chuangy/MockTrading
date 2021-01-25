#!/usr/bin/env python3.8
'''
book.py

22/03/2020 Colin Huang

Basic OrderBook class
The book is zero indexed at the top of the book for both 
bids and asks. Bids and asks are lists of PricePoints

- Updating top of book:     O(n)
- Updating end of book:     O(1)
- Updating existing price:  O(1)
- get_quote():              O(1)
- as_string():              O(n)
- top_n(n):                 O(1)

PricePoint is a simple container for a price and a size
Important assignment and comparison operations on PricePoints
are overloaded so that they can be used easily
'''

import abc
import json
from collections import deque

import util.helpers as util

class Order(abc.ABC):
    def __init__(
        self, player, room, order_id : str, price : float, size : int, direction : str, instrument: str
    ):
        self._direction = direction
        self._order_id = order_id
        self._player = player
        self._room = room
        self._price = price
        self._size = size
        self._remaining_size = size
        self._instrument = instrument
        self._status = 'active'

    def get_size(self):
        return self._remaining_size

    def get_price(self):
        return self._price

    def get_direction(self):
        return self._direction # ask, bid

    def get_status(self):
        return self._status

    def get_order_id(self):
        return self._order_id

    def get_player_name(self):
        return self._player._player_name

    async def send_update(self):
        payload = {
            'type' : 'OrderUpdate',
            'data' : {
                'instrument' : self._instrument,
                'order_id' : self._order_id,
                'size' : self._size,
                'remaining_size' : self._remaining_size,
                'price' : self._price,
                'direction' : self._direction,
                'status' : self._status,
            }
        }
        await self._player.send_message(payload)

    async def send_trade(self, size, price):
        if self._direction == 'ask':
            trade_direction = 'sell'
        elif self._direction == 'bid':
            trade_direction = 'buy'
        if price is None:
            price = self._price
        else:
            price = price

        payload = {
            'type' : 'TradeUpdate',
            'data' : {
                'price' : price,
                'size' : self._size,
                'direction' : trade_direction
            }
        }
        await self._player.send_message(payload)

    async def fill(self, size, price=None):
        if size > self._remaining_size:
            raise Exception('Trying to fill more than existing size')
        else:
            self._remaining_size -= size
        
        if self._remaining_size == 0:
            self._status = 'filled'

        await self.send_update()
        await self.send_trade(size, price)

        if price is None:
            util.print_core(f'Filled {size} at a price {self._price} ({self._player._player_name}) (maker)')
        else:
            util.print_core(f'Filled {size} at a price {price} ({self._player._player_name}) (taker)')
            await self._room.new_trade(self._instrument, price, size, self._direction)

        await self._room.update_positions(
            self._player._player_name, 
            self._instrument, 
            self._price, size, 
            self._direction
        )

    async def cancel_order(self):
        self._status = 'cancelled'
        self._remaining_size = 0
        await self.send_update()

    def __eq___(self, other):
        if isinstance(other, Order):
            if (self._order_id == other._order_id and self._instrument == other._instrument):
                return True
            else:
                return False
        return False

    def __repr__(self):
        return json.dumps(self.as_dict(), indent=4)

    def as_dict(self):
        return {
            'direction': self._direction,
            'price': self._price,
            'player': self._player._player_name,
            'room' : self._room._name,
            'size' : self._size,
            'remaining_size' : self._remaining_size,
            'status': self._status,
            'order_id' : self._order_id,
        }

class PricePoint(abc.ABC):
    '''
    A PricePoint contains a price and a size at the price
    No information about bid / ask is given
    '''

    def __init__(self, price):
        util.print_core('Initiallising new price point!')
        self.price = price
        self.size = 0
        self.type = None # ask, bid
        self.queue = deque([])

    async def cancel_order(self, player_name):
        removal = []
        for o in self.queue:
            if o.get_player_name() == player_name:
                self.size -= o.get_size()
                await o.cancel_order()
                removal.append(o)
        if len(removal) == 0:
            util.print_core(f'Unable to find any orders for {player_name}')
        else:
            for o in removal:
                self.queue.remove(o)
                util.print_core(f'Removing {o.get_order_id()} from queue')
            print(self)

        if self.size == 0:
            self.type = None

    async def new_order(self, order : Order):
        util.print_core(f'Processing new order at price: {self.price}!')
        size = order.get_size()
        ask_bid = order.get_direction()
        
        if self.type is None:
            util.print_core(f'No current orders at {self.price}!')
            self.type = ask_bid
            self.size += size
            self.queue.append(order)
        elif self.type == ask_bid:
            self.size += size
            self.queue.append(order)
        elif self.type != ask_bid: # There is overlap in the price points
            util.print_core('Overlap found in PricePoint')
            remaining_size = size
            if size <= self.size:
                while remaining_size != 0:
                    top_order = self.queue.popleft()
                    top_size = top_order.get_size()
                    if top_size <= remaining_size:
                        await top_order.fill(top_size)
                        await order.fill(top_size, price=self.price)
                        remaining_size -= top_size
                        self.size -= top_size
                    else:
                        await top_order.fill(remaining_size)
                        await order.fill(remaining_size, price=self.price)
                        self.size -= remaining_size
                        remaining_size -= remaining_size
                        self.queue.appendleft(top_order)
            else:
                while self.size != 0:
                    top_order = self.queue.popleft()
                    top_size = top_order.get_size()
                    await top_order.fill(top_size)
                    await order.fill(top_size, price=self.price)
                    self.size -= top_size
                    remaining_size -= top_size

                if order.get_price() == self.price:
                    self.queue.append(order)
                    self.type = ask_bid
                    self.size = remaining_size
                    util.print_core(f'Order was partially filled {remaining_size} remains')
        else:
            util.print_core(f'Strange behavour: {self.type}, {ask_bid}')

    def get_price(self):
        return self.price

    def get_size(self):
        return self.size

    def get_direction(self):
        return self.type

    def as_dict(self, t=None):
        entry = {}
        entry['price'] = self.price
        entry['size'] = self.size
        if t:
            assert(t == 'ask' or t == 'bid')
            entry['type'] = t
        return entry

    def __eq__(self, other):
        if not other:
            return False
        elif type(other) == type(self):
            return self.price == other.price
        elif type(other) == float:
            return self.price == other
        elif type(other) == int:
            return self.price == other
        else:
            raise TypeError(f'Unknown type: {type(other)}')

    def __lt__(self, pp):
        return self.price < pp.price

    def __le__(self, pp):
        return self.price <= pp.price

    def __gt__(self, pp):
        return self.price > pp.price

    def __ge__(self, pp):
        return self.price >= pp.price

    def __iadd__(self, other):
        if type(other) == type(self):
            if self.price == other.price:
                self.size += other.size
                return self
            else:
                raise TypeError('PricePoint prices must match')
        elif type(other) == int:
            self.size += other
            return self
        else:
            raise TypeError(f'Attempting to add unknown type: {type(other)}')

    def __isub__(self, size: int):
        self.__iadd__(- size)

    def __repr__(self):
        return json.dumps({
            'price' : self.price,
            'size' : self.size,
            'direction' : self.type,
            'queue' : [o.as_dict() for o in self.queue]
        }, indent=4)

class OrderBook(abc.ABC):
    def __init__(self, symbol: str, tick_size: float):
        self.symbol = symbol
        self.clear()

        self.tick_size = tick_size  # The smallest increment
        self.last_order_id = 0

    def generate_id(self):
        self.last_order_id += 1
        return self.last_order_id

    async def cancel_order(self, player_name, price, direction):
        if direction == 'ask':
            i = int((price - self.ba) / self.tick_size)
            pp = self.asks[i]
        elif direction == 'bid':
            i = int((self.bb - price) / self.tick_size)
            pp = self.bids[i]
        else:
            raise ValueError('Unknown direction type')
        
        await pp.cancel_order(player_name)
        if pp.get_size() == 0:
            self.delete(price, direction)

    def as_dict(self):
        a = [x for x in self.asks if x is not None]
        b = [x for x in self.bids if x is not None]

        out = {
            'symbol': self.symbol,
            'bids': b,
            'asks': a,
            'bb': self.bb,
            'ba': self.ba
        }
        return out

    def __repr__(self):
        return self.as_string(indent=4)

    def as_string(self, indent=None):
        symbol = self.symbol
        asks = [x.as_dict('ask') for x in self.asks if x is not None]
        bids = [x.as_dict('bid') for x in self.bids if x is not None]

        out = {}
        out['type'] = 'OrderbookUpdate'
        out['symbol'] = symbol
        out['data'] = asks + bids
        return json.dumps(out, indent=indent)

    def as_update(self):
        symbol = self.symbol
        asks = [x.as_dict('ask') for x in self.asks if x is not None]
        bids = [x.as_dict('bid') for x in self.bids if x is not None]

        out = {}
        out['type'] = 'OrderbookUpdate'
        out['symbol'] = symbol
        out['data'] = asks + bids
        return out

    def top_n(self, n):
        try:
            asks = [x.as_dict('ask') for x in self.asks if x is not None][:n]
            bids = [x.as_dict('bid') for x in self.bids if x is not None][:n]

            out = {}
            out['type'] = 'OrderbookTopN'
            out['symbol'] = self.symbol
            out['data'] = asks + bids
            return out
        except:
            print('Error...\n')

    def get_quote(self):
        if len(self.bids) == 0 or len(self.asks) == 0:
            return (None, None)
        return (self.bids[0], self.asks[0])

    def get_name(self):
        return self.symbol

    def clear(self):
        self.bids = []
        self.asks = []

        self.bb = None  # Best Bid
        self.ba = None  # Best Ask        

    async def new_order(self, order):
        if isinstance(order, dict):
            o = Order(
                order['player'], 
                order['room'], 
                self.generate_id(), 
                order['price'], 
                order['size'], 
                order['direction'],
                order['instrument']
            )
            await o.send_update()
            await self.new_order(o)
        elif isinstance(order, Order):
            price = order.get_price()
            ask_bid = order.get_direction()
            if price <= 0:
                return
            if ask_bid == 'ask':
                if self.bb is not None and price <= self.bb: # Spread cross: Trade will happen for all prices >= price
                    util.print_core(f'Matching trades')
                    deletion = []
                    for best_pp in self.bids:
                        if best_pp is None:
                            continue
                        remaining_size = order.get_size()
                        if remaining_size == 0:
                            break
                        trade_price = best_pp.get_price()
                        if trade_price < price:
                            break
                        await best_pp.new_order(order)
                        if best_pp.get_size() == 0 or best_pp.get_direction() == 'ask': # Dropped an entire pricepoint
                            deletion.append(trade_price)
                    for p in deletion:
                        self.delete(p, 'bid') # Remove the zero sized ones
                        # This should shift the best bid to leq than price

                    if order.get_status() != 'filled':
                        await self.new_order(order) # price should not be leq best bid
                else: # No trades
                    list_size = len(self.asks)
                    if list_size == 0:
                        pp = PricePoint(price)
                        await pp.new_order(order)
                        self.asks.append(pp)
                        self.ba = price
                    else:
                        i = int((price - self.ba) / self.tick_size)
                        if i > list_size - 1:
                            self.asks += [None] * (i - list_size + 1)
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.asks[i] = pp
                        elif i < 0:
                            self.asks[0:0] = [None] * abs(i)
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.asks[0] = pp
                            self.ba = price
                        elif self.asks[i] is None:
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.asks[i] = pp
                        elif self.asks[i] is not None:
                            await self.asks[i].new_order(order)
                        else:
                            util.print_core('Something bad happened')

            elif ask_bid == 'bid':
                if self.ba is not None and price >= self.ba: # Spread cross: Trade will happen for all prices >= price
                    util.print_core(f'Matching trades')
                    deletion = []
                    for best_pp in self.asks:
                        if best_pp is None:
                            continue
                        remaining_size = order.get_size()
                        if remaining_size == 0:
                            break
                        trade_price = best_pp.get_price()
                        if trade_price > price:
                            break
                        await best_pp.new_order(order)
                        if best_pp.get_size() == 0 or best_pp.get_direction() == 'bid': # Dropped an entire pricepoint
                            deletion.append(trade_price)
                    for p in deletion:
                        self.delete(p, 'ask') # Remove the zero sized ones
                        # This should shift the best ask to geq than price

                    if order.get_status() != 'filled':
                        await self.new_order(order) # price should not be leq best bid
                else: # No trades
                    list_size = len(self.bids)
                    if list_size == 0:
                        util.print_core('Currently no bids, adding first!')
                        pp = PricePoint(price)
                        await pp.new_order(order)
                        self.bids.append(pp)
                        self.bb = price
                    else:
                        i = int((self.bb - price) / self.tick_size)
                        if i > list_size - 1:
                            util.print_core('Bid is the new lowest, adding at end!')
                            self.bids += [None] * (i - list_size + 1)
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.bids[i] = pp
                        elif i < 0:
                            util.print_core('Bid is the new best, adding at front!')
                            self.bids[0:0] = [None] * abs(i)
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.bids[0] = pp
                            self.bb = price
                        elif self.bids[i] is None:
                            util.print_core(f'Currently no bids at {price} - making new PricePoint')
                            pp = PricePoint(price)
                            await pp.new_order(order)
                            self.bids[i] = pp
                        elif self.bids[i] is not None:
                            util.print_core(f'There are already bids at {price} - adding to PricePoint')
                            await self.bids[i].new_order(order)
                        else:
                            util.print_core('Something bad happened')
            else:
                raise TypeError('Must be bid or ask')
        else:
            raise TypeError('Unknown type')

    def delete(self, price: float, ask_bid: str) -> bool:
        if ask_bid == 'ask':
            list_size = len(self.asks)
            if list_size == 0:
                return False
            else:
                i = int((price - self.ba) / self.tick_size)
                if i > list_size - 1:
                    return False
                elif i < 0:
                    return False
                elif i == 0:
                    if list_size == 1:
                        self.asks = []
                        self.ba = None
                        return True
                    n_pop = 1
                    for i in range(1, list_size - 1):
                        # Potentially O(n) at worst...
                        if self.asks[i] == None:
                            n_pop += 1
                        else:
                            break

                    # We remove the first element and all
                    # subsequent None elements to reset the
                    # indexing to zero at the top of book
                    self.asks = self.asks[n_pop:]
                    self.ba = self.asks[0].get_price()
                    return True
                elif i == list_size - 1:
                    n_pop = 1
                    for j in range(1, list_size):
                        if self.asks[i - j] == None:
                            n_pop += 1
                        else:
                            break
                    self.asks = self.asks[:list_size - n_pop]
                    return True
                else:
                    self.asks[i] = None
                    return True
        elif ask_bid == 'bid':
            list_size = len(self.bids)
            if list_size == 0:
                return False
            else:
                i = int((self.bb - price) / self.tick_size)
                if i > list_size - 1:
                    return False
                elif i < 0:
                    return False
                elif i == 0:
                    util.print_core('Deleting the best bid PricePoint!')
                    if list_size == 1:
                        self.bids = []
                        self.bb = None
                        return True
                    n_pop = 1
                    for i in range(1, list_size):
                        # Potentially O(n) at worst...
                        if self.bids[i] == None:
                            n_pop += 1
                        else:
                            # Update best bid
                            break

                    # We remove the first element and all
                    # subsequent None elements to reset the
                    # indexing to zero at the top of book
                    self.bids = self.bids[n_pop:]
                    self.bb = self.bids[0].get_price()
                    return True
                elif i == list_size - 1:
                    util.print_core('Deleting the last bid PricePoint!')
                    n_pop = 1
                    for j in range(1, list_size):
                        if self.bids[i - j] == None:
                            n_pop += 1
                        else:
                            break
                    self.bids = self.bids[:list_size - n_pop]
                    return True
                else:
                    util.print_core(f'Deleting the {price} bid PricePoint!')
                    self.bids[i] = None
                    return True
        else:
            raise TypeError('Must be bid or ask')

    def __eq__(self, other):
        if type(other) == str:
            return self.symbol == other
        elif type(other) == type(self):
            return self.symbol == other.symbol
        else:
            raise TypeError

    def __getitem__(self, key):
        if type(key) == float: # If key is a price
            if float >= self.ba:  # Ask
                i = int((self.ba - key) / self.tick_size)
                return self.asks[i]
            elif float <= self.bb:  # Bid
                i = int((key - self.bb) / self.tick_size)
                return self.bids[i]
            else:
                return None
        elif type(key) == PricePoint:
            return self.__getitem__(key.get_price())

    def __setitem__(self, key, value):
        pass

    def __getslice__(self, key):
        pass