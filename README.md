# MockTrading
WebApp to simulate mock trading - written in Python/ReactJS.

## Dependencies
Requires `python3.8` and `NodeJS'.
```
sudo apt install python3.8 python3.8-venv
npm install --global yarn
yarn global add pm2
```
Also make sure that `export PATH="$PATH:$(yarn global bin)"` is in the `.bashrc` so that pm2 can be found by bash.

## Usage (Hosting)
Clone the directory 
`git clone https://github.com/Chuangy/MockTrading`

Create a `.env` file in `frontend/` to initialise the environmental variables for the ReactJS application. It should contain the following information:
```
REACT_APP_PUBLIC_HOST={your_public_ip_address}
REACT_APP_PRIVATE_HOST={your_private_ip_address}
REACT_APP_PORT="8887"
```

Proceed to build the frontend ReactJS application.
```
cd frontend/
yarn install
yarn build
```
From the root directory, run the following:
```
pm2 start mocktrading.config.js --env production
```
The logs can be retrieved using
```
pm2 logs
```
and resources can be monitored using 
```
pm2 monit
```

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
