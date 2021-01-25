export class Orderbook {
  constructor() {
    console.log("Creating new book...");
    this.book = {};
    this.orders = {};
  }

  copy() {
    return this;
  }

  getBook() {
    return JSON.parse(JSON.stringify(this.book));
  }

  getAggregatedActiveOrders() {
    let out = {};
    const symbols = Object.keys(this.orders);
    symbols.forEach((s) => {
      out[s] = {};
      Object.values(this.orders[s]).forEach((o) => {
        if (o.active) {
          const price = o.price;
          if (Object.keys(out[s]).includes(price.toString())) {
            out[s][price].size = out[s][price].size + o.size;
          } else {
            out[s][price] = {
              size: o.size,
              direction: o.direction,
            };
          }
        }
      });
    });
    return out;
  }

  getActiveOrderID(symbol, price) {
    let out = [];
    const orders = this.orders[symbol];
    Object.values(orders).forEach((o) => {
      if (o.price.toString() === price && o.active) {
        out.push(o.order_id);
      }
    });
    return out;
  }

  onUpdate(message) {
    const symbol = message.symbol;
    if (!this.book[symbol]) {
      console.log(`Initialising ${symbol}`);
      this.book[symbol] = {
        ask: {},
        bid: {},
      };
    }

    this.book[symbol] = {
      ask: {},
      bid: {},
    };
    message.data.forEach((update) => {
      this.updateBook(symbol, update);
    });
  }

  onDelete(message) {
    const symbol = message.symbol;
    message.data.forEach((pp) => {
      this.deleteEntry(symbol, pp);
    });
  }

  onNewOrders(message) {
    const data = message.data;
    const instrument = data.instrument;
    if (!this.orders[instrument]) {
      this.orders[instrument] = {};
    }
    const order_id = data.order_id;
    this.orders[instrument][order_id] = {
      active: data.status === 'active' ? true : false,
      price: data.price,
      size: data.size,
      direction: data.direction,
      order_id: data.order_id,
    };
  }

  onUpdateOrders(message) {
    const data = message.data;
    for (let i = 0; i < data.length; i++) {
      const order_id = data[i].order_id;
      const active = data[i].active;
      const size = data[i].size;
      const price = data[i].price;

      const symbols = Object.keys(this.orders);
      for (let j = 0; j < symbols.length; j++) {
        const s = symbols[j];
        if (Object.keys(this.orders[s]).includes(order_id)) {
          this.orders[s][order_id].active = active ? active : false;
          this.orders[s][order_id].size = size
            ? size
            : this.orders[s][order_id].size;
          this.orders[s][order_id].price = price
            ? price
            : this.orders[s][order_id].price;
        }
      }
    }
  }

  onDeleteOrders(message) {
    const data = message.data;
    const symbols = Object.keys(this.orders);
    for (let i = 0; i < data.length; i++) {
      const order_id = data[i];
      for (let j = 0; j < symbols.length; j++) {
        const s = symbols[j];
        delete this.orders[s][order_id];
      }
    }
  }

  updateBook(symbol, update) {
    const type = update.type; // 'ask' or 'bid'
    const price = update.price;
    const size = update.size;
    this.book[symbol][type][price] = size;
  }

  deleteEntry(symbol, pp) {
    const type = pp.type;
    const price = pp.price;
    delete this.book[symbol][type][price];
  }
}
