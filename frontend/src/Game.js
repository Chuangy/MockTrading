import React from "react";
import {
	Form,
	Input,
	Select,
	Radio,
	InputNumber
} from 'antd';

import Loader from 'react-loader-spinner'

import "antd/dist/antd.css";
import "react-loader-spinner/dist/loader/css/react-spinner-loader.css"

import './Game.css';
import { Orderbook } from "./Orderbook";

export class Game extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			last_render_time: null,
			ws: null,
			current_room: null,
			current_players: [],
			rooms: [],
			players: [],
			player_name: "no_name",
			status: "none",
			cards: [],
			revealed_cards: {},
			instruments: [],
			books: new Orderbook(),
			positions: [],
			orders: [],
			trades: [],
		}
	}

	componentDidMount() {
		this.connect();
		setInterval(() => this.setState({
			last_render_time: Date.now(),
		}), 200)
	}
	
	connect = () => {
		let ws = new WebSocket("ws://localhost:8887");
		ws.onopen = () => {
			console.log("Conncted to the websocket!");
			this.setState({ ws: ws });

			ws.send("")
			ws.send(JSON.stringify({type: "NewRoom", data: {name: 'TestRoom'}}))
			ws.send("")
			ws.send(JSON.stringify({
				type: "NewPlayer", data: {name: 'unnamed_player'}
			}))
		};

		ws.onmessage = (event) => {
			const message = JSON.parse(event.data);

			switch (message.type) {
				case "Info":
					console.log(message.status)
					break;
				case "PlayerDetails":
					this.setState({
						player_name: message.data
					});
					break;
				case "PlayerUpdate":
					console.log('Received player update!')
					this.setState({
						players: message.data
					});
					break;
				case "RoomUpdate":
					console.log('Received room update!')
					this.setState({
						rooms: message.data
					});
					break;
				case "RoomPlayersUpdate":
					console.log('Received update of players in room!')
					if (this.state.current_room === message.data.room) {
						this.setState({
							current_players: message.data.players
						});
					}
					break;
				case "GameStart":
					console.log('Received cards from the dealer!')
					this.setState({
						cards: message.data.cards,
						status: "started"
					});
					break;
				case "RevealedCards":
					console.log('Received new revealed cards!')
					this.setState({
						revealed_cards: message.data,
					});
					break;
				case "InstrumentsUpdate":
					console.log('Received new instruments')
					this.setState({
						instruments: message.data
					})
					break;
				case "PositionUpdate":
					console.log('Received new position')
					console.log(message.data)
					this.setState({
						positions: message.data
					});
					break;
				case "OrderbookUpdate":
					console.log('Received new orderbok')
					let books = this.state.books;
					books.onUpdate(message)
					this.setState({books : books});
					break;
				case "OrderUpdate":
					console.log('Received new order')
					let books_copy = this.state.books;
					books_copy.onNewOrders(message)
					this.setState({books : books_copy});
					break;
				case "Trade":
					console.log('Received trades')
					this.setState({trades : message.data});
					break;
				default:
					console.log(`Unknown message: ${JSON.stringify(message)}`)
			}
		};
	};

	handleNewRoom(r) {
		console.log(`Creating new room ${r}`)
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({type: "NewRoom", data: {name: r}}))
	}

	handleJoinRoom(r) {
		if (this.state.player_name === "no_name") {
			console.log('Please enter name first...')
		}
		else {
			this.setState({
				current_room: r
			});
			this.state.ws.send("")
			this.state.ws.send(JSON.stringify({
				type: "JoinRoom", data: {room: r, player: this.state.player_name}
			}))
		}
	}

	handleLeaveRoom(r) {
		this.setState({
			current_room: null,
			current_players: [],
			cards: [],
			revealed_cards: {},
			status: "none",
			instruments: [],
			books: new Orderbook(),
			positions: [],
			orders: [],
			trades: [],
		});
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "LeaveRoom", data: {room: r, player: this.state.player_name}
		}))
	}

	handleStart() {
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "StartGame", data: {room: this.state.current_room}
		}));
	}

	handleRevealCard(number, suit) {
		console.log(`Revealing card ${number}-${suit} to room..`)
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "RevealCard", data: {
				room: this.state.current_room,
				player: this.state.player_name,
				card: [number, suit]
			}
		}));
	}

	handleNewInstrument(name, type, strike) {
		console.log('Sending request to make new instrument')

		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "NewInstrument", 
			data: {
				room: this.state.current_room,
				name: name,
				type: type,
				strike: strike,
			}
		}));
	}

	handleNewOrder(instrument, price, size, direction) {
		console.log(`Sending new order for ${instrument} ${price} ${size} ${direction}`)
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "NewOrder", 
			data: {
				room: this.state.current_room,
				player: this.state.player_name,
				instrument: instrument,
				price: price,
				size: size,
				direction: direction
			}
		}));
	}

	handleCancelOrder(instrument, price, direction) {
		console.log(`Cancelling order for ${instrument} ${price} ${direction}`)
		this.state.ws.send("")
		this.state.ws.send(JSON.stringify({
			type: "CancelOrder", 
			data: {
				room: this.state.current_room,
				player: this.state.player_name,
				instrument: instrument,
				price: price,
				direction: direction
			}
		}));
	}

	shouldComponentUpdate(nextProps, nextState) {
		if (JSON.stringify(nextProps) !== JSON.stringify(this.props)) {
			return true;
		}
		else if (JSON.stringify(nextState) !== JSON.stringify(this.state)) {
			return true;
		}
		return false;
	}

	render() {
		const books = this.state.books.getBook();
		const orders = this.state.books.getAggregatedActiveOrders();
		const trades = this.state.trades;
		return (
			<div className="game_wrapper">
				<div className="left_bar">
					<Player
						player_name={this.state.player_name}
						ws={this.state.ws}
					/>
					<Lobby players={this.state.players}/>
					<AvailableRooms 
						current_room={this.state.current_room}
						rooms={this.state.rooms}
						onJoinRoom={this.handleJoinRoom.bind(this)}
						onLeaveRoom={this.handleLeaveRoom.bind(this)}
						onNewRoom={this.handleNewRoom.bind(this)}
					/>
				</div>
				<div className="right_bar">
					<Room 
						room={this.state.current_room}
						player_name={this.state.player_name}
						status={this.state.status}
						players={this.state.current_players}
						onStart={this.handleStart.bind(this)}
						onRevealCard={this.handleRevealCard.bind(this)}
						cards={this.state.cards}
						revealed_cards={this.state.revealed_cards}
					/>
				</div>
				{this.state.status === "none" ?
					<div className="loading_wrapper">
						<div>
							<h1>Waiting for game start...</h1>
						</div>
						<Loader
							type="BallTriangle"
							color="#1E1E1E"
							height={200}
							width={200}
						/> 
						<div>
							<h2>First enter your name if you haven't already done so...</h2>
							<h3>Then join a room....</h3>
						</div>
					</div> :
					<> 
					<div className="tool_bar">
						<NewOrders
							instruments={this.state.instruments}
							onNewOrder={this.handleNewOrder.bind(this)}
						/>
						<Positions
							instruments={this.state.instruments}
							positions={this.state.positions}
						/>
						<Instruments
							instruments={this.state.instruments}
							onNewInstrument={this.handleNewInstrument.bind(this)}
						/>
					</div>
					<div className="main_canvas">
						<Books
							books={books}
							orders={orders}
							instruments={this.state.instruments}
							onCancelOrder={this.handleCancelOrder.bind(this)}
						/>
						<Trades
							trades={trades}
						/>
					</div>
					</>
				}
			</div>
		)
	}
}

class Trades extends React.Component {
	render() {
		const trades = this.props.trades ? Object.values(this.props.trades).flat() : [];
		return (
			<div className="trade_wrapper">
				<h1>Trades</h1>
				
				<div className="trades_row heading" key="heading">
					<div className="trades_instrument">
						Instrument
					</div>
					<div className="trades_price">
						Price
					</div>
					<div className="trades_size">
						Size
					</div>
				</div>
				{trades.reverse().map((t) => {
					return (
						<div className={`trades_row ${t['direction']}`} key={t['timestamp']}>
							<div className="trades_instrument">
								{t['instrument']}
							</div>
							<div className="trades_price">
								{t['price']}
							</div>
							<div className="trades_size">
								{t['size']}
							</div>
						</div>
					)
				})}
			</div>
		)
	}
}

class NewOrders extends React.Component {
	constructor(props) {
		super(props)
		this.state = {
			instrument: null,
			price: null,
			size: null,
			direction: "bid",
		}
	}
	handleValueChange(changedValues, allValues) {
		this.setState({...changedValues});
	}

	render() {
		const instruments = this.props.instruments;
		const width = "75%";
		return (
			<div className="new_order_form">
				<h1>New Order</h1>
				<Form 
					labelCol={{ span: 8 }}
					wrapperCol={{ span: 16 }}
					labelAlign="right"
					layout="horizontal"
					size="default"
					onValuesChange={this.handleValueChange.bind(this)}
					initialValues={this.state}
				>
					<Form.Item label="Instrument" name="instrument">
						<Select style={{width: width}}>
							{instruments.map((i) => {
								return <Select.Option value={i} key={i}>{i}</Select.Option>
							})}
						</Select>
					</Form.Item>
					<Form.Item label="Price" name="price">
						<InputNumber min={0} precision={0} style={{width: width, textAlign: "center"}}/>
					</Form.Item>
					<Form.Item label="Size" name="size">
						<InputNumber min={0} precision={0} style={{width: width, textAlign: "center"}}/>
					</Form.Item>
				</Form>
				<div className="button_row">
					<div 
						className="bid_button" 
						onClick={this.props.onNewOrder.bind(this, this.state.instrument, this.state.price, this.state.size, "bid")}
					>
						Bid
					</div>
					<div 
						className="ask_button"
						onClick={this.props.onNewOrder.bind(this, this.state.instrument, this.state.price, this.state.size, "ask")}
					>
						Ask
					</div>
				</div>
			</div>
		)
	}
}

class Positions extends React.Component {
	constructor(props) {
		super(props);
	}

	render() {
		const n_instruments = this.props.instruments.length;
		return (
			<div className="positions_wrapper">
				<h1>Positions</h1>
				<div className="position_row heading" key="heading">
								<div className="position_instrument">
									Instrument
								</div>
								<div className="position_size">
									Size
								</div>
								<div className="position_price">
									Average Price
								</div>
							</div>
				{this.props.instruments.map((i, index) => {
					return (
						this.props.positions[i] ?
							<div className={`position_row ${index === n_instruments - 1 ? "last" : ""}`} key={i}>
								<div className="position_instrument">
									{i}
								</div>
								<div className="position_size">
									{this.props.positions[i]['size']}
								</div>
								<div className="position_price">
									{this.props.positions[i]['average_price'] !== 0 ? this.props.positions[i]['average_price'] : "N/A"}
								</div>
							</div> : ""
					)
				})}
			</div>
		)
	}
}

class Instruments extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			new_instrument_type: "call",
			new_instrument_strike: null,
		}
	}

	handleValueChange(changedValues, allValues) {
		this.setState({...changedValues});
	} 

	render() {
		const new_instrument_name = `${this.state.new_instrument_strike}-${this.state.new_instrument_type.toUpperCase()}`
		return (
			<div className="instruments_wrapper">
				<div className="new_instrument">
					<h1>New Instrument</h1>
					<Form 
						labelCol={{ span: 8 }}
						wrapperCol={{ span: 16 }}
						labelAlign="right"
						layout="horizontal"
						size="default"
						onValuesChange={this.handleValueChange.bind(this)}
						initialValues={{new_instrument_type: this.state.new_instrument_type}}
					>
						<Form.Item label="Instrument type" name="new_instrument_type">
							<Radio.Group optionType="button" buttonStyle="solid" >
								<Radio.Button value="call">Call</Radio.Button>
								<Radio.Button value="put">Put</Radio.Button>
							</Radio.Group>
						</Form.Item>
						<Form.Item label="Strike" name="new_instrument_strike">
							<InputNumber min={0}/>
						</Form.Item>
					</Form>
					<div className="new_instrument_button" 
						onClick={this.props.onNewInstrument.bind(this, new_instrument_name, this.state.new_instrument_type, this.state.new_instrument_strike)}
					>
						Create!
					</div>
				</div>
			</div>
		)
	}
}

class Books extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			active_instruments : [],
		}
	}

	shouldComponentUpdate(nextProps, nextState) {
		if (JSON.stringify(nextProps) !== JSON.stringify(this.props)) {
			return true;
		}
		else if (JSON.stringify(nextState) !== JSON.stringify(this.state)) {
			return true;
		}
		return false;
	}

	handleSelect(instrument) {
		let active_instruments = this.state.active_instruments.slice(0);
		if (active_instruments.includes(instrument)) {
			active_instruments.splice(active_instruments.indexOf(instrument), 1)
		}
		else {
			active_instruments = [...active_instruments, instrument]
		}
		this.setState({active_instruments : active_instruments})
	}

	render() {
		const active_instruments = this.state.active_instruments;
		const instruments = this.props.instruments ? this.props.instruments : [];
		return (
			<div className="book_wrapper">
				<h1>Books</h1>
				<div className="instrument_select">
					{instruments.map((i) => {
						return (
							<div 
								className={`option ${active_instruments.includes(i) ? "selected" : "unselected"}`} 
								style={{width: `${100 / instruments.length}%`}}
								key={i}
								onClick={this.handleSelect.bind(this, i)}
							>
								{i}
							</div>
						)
					})}
				</div>
				{active_instruments.map((i) => {
					return (
						<Book
							book={this.props.books[i]}
							orders={this.props.orders[i]}
							instrument={i}
							width={`${100 / active_instruments.length}%`}
							key={i}
							onCancelOrder={this.props.onCancelOrder.bind(this)}
						/>
					)
				})}
			</div>
		)
	}
}

class Book extends React.Component {
	shouldComponentUpdate(nextProps, nextState) {
		if (JSON.stringify(nextProps) !== JSON.stringify(this.props)) {
			return true;
		}
		else if (JSON.stringify(nextState) !== JSON.stringify(this.state)) {
			return true;
		}
		return false;
	}

	render() {
		const asks = this.props.book ? this.props.book['ask'] : {};
		const bids = this.props.book ? this.props.book['bid'] : {};
		const orders = this.props.orders ? this.props.orders : {}

		return (
			<div className="book" style={{width: this.props.width ? this.props.width : "100%"}}>
				<h2>{this.props.instrument}</h2>
				<div className="bids">
					<div className="book_row heading">
						<div className="book_order">Orders</div>
						<div className="book_size">Size</div>
						<div className="book_price">Price</div>
					</div>
					{Object.keys(bids).sort((a, b) => {return b - a}).map((price) => {
						return (
							<div className="book_row" key={price}>
								{orders[price] ?
									<div 
										className="book_order active"
										onClick={this.props.onCancelOrder.bind(this, this.props.instrument, price, "bid")}
									>
										{orders[price]['size']}
									</div> :
									<div className="book_order">-</div>
								}
								<div className="book_size">{bids[price]}</div>
								<div className="book_price">{price}</div>
							</div>
						)
					})}
				</div>
				<div className="asks">
					<div className="book_row heading">
						<div className="book_price">Price</div>
						<div className="book_size">Size</div>
						<div className="book_order">Orders</div>
					</div>
					{Object.keys(asks).sort((a, b) => {return a - b}).map((price) => {
						return (
							<div className="book_row" key={price}>
								<div className="book_price">{price}</div>
								<div className="book_size">{asks[price]}</div>
								{orders[price] ?
									<div 
										className="book_order active"
										onClick={this.props.onCancelOrder.bind(this, this.props.instrument, parseInt(price), "ask")}
									>
										{orders[price]['size']}
									</div> :
									<div className="book_order">-</div>
								}
							</div>
						)
					})}
				</div>
			</div>
		)
	}
}

class Player extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			player_name: "Enter your name..."
		}
	}

	handleNameChange(e) {
		this.setState({player_name: e.target.value});
	}

	handleNameSubmit(e) {
		this.props.ws.send("");
		this.props.ws.send(JSON.stringify({
			type: "NewPlayer", data: {name: this.state.player_name}
		}));
		e.preventDefault();
	}

	render() {
		return (
			<div className="player">
				<div className="label">Player details</div>
				<div className="player_name_changer">
					{this.props.player_name === "no_name" ? 
						<form onSubmit={this.handleNameSubmit.bind(this)}>
							<input value={this.state.player_name} onChange={this.handleNameChange.bind(this)}/>
						</form> :
						<div className="player_name">{this.props.player_name}</div>
					}
				</div>
			</div>
		)
	}
}

class Card extends React.Component {
	suit_mapping(s) {
		let suit;
		switch (s) {
			case ('S'):
				suit = 
				<div className="card_suit">
					&spades;
				</div>
				break;
			case ('H'):
				suit = 
				<div className="card_suit">
					&hearts;
				</div>
				break;
			case ('C'):
				suit =
				<div className="card_suit">
					&clubs;
				</div>
				break;
			case ('D'):
				suit  =
				<div className="card_suit">
					&diams;
				</div>
				break;
			default:
				suit = 
				<div className="card_suit">
					&alefsym;
				</div>
		}
		return suit;
	}
	render() {
		const number = this.props.data[0];
		const suit = this.props.data[1];
		
		const revealed_cards = (
			this.props.revealed_cards ? 
				Object.values(this.props.revealed_cards).flat() :
				[]
		).map((a) => {
			return JSON.stringify(a)
		});
		const colour = revealed_cards.includes(JSON.stringify([number, suit])) ? 
			"revealed" : "unrevealed";
		
		return (
			<div 
				className={`card ${colour}`}
				onClick={this.props.onRevealCard.bind(this, number, suit)}
			>
				<div className="card_number">
					{number}
				</div>
				{this.suit_mapping(suit)}
			</div> 
		)
	}
}

class Room extends React.Component {
	constructor(props) {
		super(props);
	}

	shouldComponentUpdate(nextProps) {
		if (JSON.stringify(nextProps) !== JSON.stringify(this.props)) {
			return true;
		}
		return false;
	}

	render() {
		const players = this.props.players ? this.props.players : [];
		const n_cards = this.props.cards.length;
		const revealed_cards = this.props.revealed_cards;
		return (
			<div className="curent_room">
				<div className="label">
					{this.props.room ? this.props.room : "Not in a room"}
				</div>
				<div className="players">
					{players.reduce((acc, element) => {
						if (element === this.props.player_name) {
							return [element, ...acc];
						}
						return [...acc, element];
					}, []).map((p) => {
						let n_revealed_cards = 0;
						return (
							<div className="player_info" key={p}>
								{p === this.props.player_name ?
									<div className="player_name yourself text row" key="name">
										{p}
									</div> :
									<div className="player_name text row" key="name">
										{p}
									</div>
								}
								<div className="player_cards text row" key="cards">
									{p === this.props.player_name ?
										<div className="card_display">
											{this.props.cards.map((c) => 
												<Card 
													data={c} 
													onRevealCard={this.props.onRevealCard} 
													key={c}
													revealed_cards={this.props.revealed_cards}
												/>
											)}
										</div> :
										<div className="card_display">
											{revealed_cards[p] ? revealed_cards[p].map((c) => {
												n_revealed_cards += 1;
												return <Card 
													data={c} 
													onRevealCard={console.log} 
													key={c}
												/>
											}) : ""}
											{[...Array(n_cards - n_revealed_cards).keys()].map((v) => 
												<Card 
													data={["?", "?"]} 
													onRevealCard={console.log} 
													key={v}
												/>)
											}
										</div>
									}
								</div>
							</div>
						)
					}
					)}
				</div>
				{this.props.room ?
					this.props.status !== "started" ? 
						(<div className="start_button" onClick={this.props.onStart}>
							Start Game
						</div>
						) :
						(<div className="started" onClick={this.props.onStart}>
							Started
						</div>
						) :
					""
				}
			</div>
		)
	}
}

class AvailableRooms extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			new_room_name: ""
		}
	}

	handleName(e) {
		this.setState({new_room_name: e.target.value});
		e.target.value = "";
	}

	render() {
		const rooms = this.props.rooms;
		return (
			<div className="room">
				<div className="label">Available rooms</div>
				{rooms.map((r) => {
					return (
						<div className="row" key={r}>
							<div className="room_name text" key={r}>{r}</div>
							{this.props.current_room !== r ? 
								<div className="button text" 
									onClick={this.props.onJoinRoom.bind(this, r)
								}>
									Join
								</div> :
								<div className="button text" 
								onClick={this.props.onLeaveRoom.bind(this, r)
							}>
								Leave
							</div>
							}
						</div>
					)
				})}
				<div className="row" key="new_room">
					<Input className="room_name text" onChange={this.handleName.bind(this)}/>
					<div className="button text" onClick={this.props.onNewRoom.bind(this, this.state.new_room_name)}>Create</div>
				</div>
			</div>
		)
	}
}

class Lobby extends React.Component {
	constructor(props) {
		super(props);
	}

	shouldComponentUpdate(nextProps) {
		if (JSON.stringify(nextProps) !== JSON.stringify(this.props)) {
			return true;
		}
		return false;
	}

	render() {
		const players = this.props.players;
		return (
			<div className='lobby'>
				<div className="label">Players</div>
				{players.map((p) => {
					return (
						<div className="row" key={p}>
							<div className="player_name text" key={p}>{p}</div>
						</div>
					)
				})}
			</div>
		)
	}
}

export default Game;