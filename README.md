# MockTrading
WebApp to simulate mock trading - written in Python/ReactJS.

## Rules
The game features N players, each of which are dealt M cards from a standard 52 card deck. Each card has an associated value, equivalent to the face number (Ace is 1, King is 13).
Each of the players then make markets and trade the sum of the `NM` cards. When the market is stale, the players each reveal a card. 
This continues until all cards are revealed, at which time the game settles.

## Features
- Lobby room before starting game
- Option to choose number of cards / players
- Orderbook with queue priority for underlying and options
- Matching engine for trades on the orderbook
- Ability to introduce new options into the market
- Front end GUI to wrap all this up
