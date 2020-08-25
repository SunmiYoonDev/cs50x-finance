# cs50x-finance

## Background
This is a web app via which you can manage portfolios of stocks. The stock-trading website let user buy and sell stocks by querying IEX for stocks’ prices.
Indeed, IEX lets you download stock quotes via their API (application programming interface) using URLs like https://cloud-sse.iexapis.com/stable/stock/aapl/quote?token=API_KEY. Notice how Apple Inc.’s symbol (AAPL) is embedded in this URL; that’s how IEX knows whose data to return.

## How to use it
Before getting started on this web, we’ll need an API key in order to be able to query IEX’s data.
In a terminal window within CS50 IDE, execute:
```
$ export API_KEY=pk_91f57f47a752445cb469c422993f54e1
```

Start Flask’s built-in web server (within finance/):
```
$ flask run
```
After register, Notice how, by default, new users will receive $10,000 in cash. 
