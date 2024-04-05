from flask import Flask, render_template, request, jsonify
from datetime import datetime
import yfinance as yf
import numpy as np
from scipy.stats import norm
from flask_cors import CORS
import math

app = Flask(__name__)
CORS(app)

def fetch_historical_data(ticker_symbol, period='90d'):
    try:   
        ticker = yf.Ticker(ticker_symbol)
        fulldf = ticker.history(period=period)
        df = fulldf['Close']
        return df
    except Exception as e:
        print("Error fetching historical data:", e)
        return None


def get_spot_price(underlying):
    try:
        ticker = yf.Ticker(underlying)
        live_price = ticker.history(period="1d").iloc[-1]["Close"]
        return live_price
    except Exception as e:
        print("Error fetching live price:", e)
        return None

def get_sigma(df):
    try:
        price_data = df.loc[:]

        if len(price_data) < 2:
            raise ValueError("Insufficient data. Historical prices data should contain at least two values.")

        returns = np.diff(price_data) / price_data[:-1]

        trading_days_per_year = 252
        sigma = np.std(returns) * np.sqrt(trading_days_per_year)
        return sigma
    except Exception as e:
        print("Error calculating historical sigma:", e)
        return None

def calculate_option_prices(S, K, T, r, sigma):
    try:
        call_price_bs = black_scholes_call(S, K, T, r, sigma)
        put_price_bs = black_scholes_put(S, K, T, r, sigma)
        call_price_binomial, put_price_binomial = binomial_option_pricing(S, K, T, r, sigma, 1000)
        call_price_mc = monte_carlo_option_price(S, K, T, r, sigma, 'call', 50000)
        put_price_mc = monte_carlo_option_price(S, K, T, r, sigma, 'put', 50000)
        call_price_trinomial = trinomial_option_pricing(S, K, T, r, 0, sigma, 1000, 'call')
        put_price_trinomial = trinomial_option_pricing(S, K, T, r, 0, sigma, 1000, 'put')
        return call_price_bs, put_price_bs, call_price_binomial, put_price_binomial, call_price_mc, put_price_mc, call_price_trinomial, put_price_trinomial
    except Exception as e:
        print("Error calculating option prices:", e)
        return None, None, None, None, None, None, None, None
    
def monte_carlo_option_price(S, K, T, r, sigma, option_type, num_simulations):
    dt = T
    rand = np.random.normal(0, 1, num_simulations)
    stock_prices = S * np.exp((r - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * rand)
    if option_type == 'call':
        payoffs = np.maximum(stock_prices - K, 0)
    elif option_type == 'put':
        payoffs = np.maximum(K - stock_prices, 0)
    else:
        raise ValueError("Invalid option type. Use 'call' or 'put'.")
    option_price = np.exp(-r * T) * np.mean(payoffs)
    return option_price

def black_scholes_call(S, K, T, r, sigma):
    if T == 0: 
        return max(S - K, 0)
    if sigma == 0: 
        return max(S - K, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def black_scholes_put(S, K, T, r, sigma):
    if T == 0:
        return max(K - S, 0)
    if sigma == 0:
        return max(K - S, 0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def binomial_option_pricing(S, K, T, r, sigma, n):
    delta_t = T / n
    u = np.exp(sigma * np.sqrt(delta_t))
    d = 1 / u
    p = (np.exp(r * delta_t) - d) / (u - d)
    stock_price = np.zeros((n + 1, n + 1))
    call_option_price = np.zeros((n + 1, n + 1))
    put_option_price = np.zeros((n + 1, n + 1))
    
    for j in range(n + 1):
        for i in range(j + 1):
            stock_price[i, j] = S * (u ** (j - i)) * (d ** i)
            if j == n:
                call_option_price[i, j] = max(stock_price[i, j] - K, 0)
                put_option_price[i, j] = max(K - stock_price[i, j], 0)
                
    for j in range(n - 1, -1, -1):
        for i in range(j + 1):
            call_option_price[i, j] = np.exp(-r * delta_t) * (p * call_option_price[i, j + 1] + (1 - p) * call_option_price[i + 1, j + 1])
            put_option_price[i, j] = np.exp(-r * delta_t) * (p * put_option_price[i, j + 1] + (1 - p) * put_option_price[i + 1, j + 1])
            
    return call_option_price[0, 0], put_option_price[0, 0]

def trinomial_option_pricing(S, K, T, r, dividend_yeild, sigma, trinomial_steps, option_type):
    option_prices = {}
    time_step = T / trinomial_steps
    up_movement = math.exp(sigma * math.sqrt(2 * time_step))
    down_movement = math.exp(-sigma * math.sqrt(2 * time_step))
    discount_factor = math.exp(r * time_step)
    u_factor = math.exp((r - dividend_yeild) * time_step / 2)
    u_half_factor = math.exp(sigma * math.sqrt(time_step / 2))
    d_half_factor = math.exp(-sigma * math.sqrt(time_step / 2))
    probability_up = ((u_factor - d_half_factor) / (u_half_factor - d_half_factor)) ** 2
    probability_down = ((u_half_factor - u_factor) / (u_half_factor - d_half_factor)) ** 2
    probability_middle = 1 - probability_up - probability_down

    for m in range(0, 2 * trinomial_steps + 1):
        if option_type == 'call':
            option_prices[(trinomial_steps, m)] = max((S * (up_movement ** max(m - trinomial_steps, 0)) * (down_movement ** max(trinomial_steps * 2 - trinomial_steps - m, 0))) - K, 0)
        elif option_type == 'put':
            option_prices[(trinomial_steps, m)] = max(K - (S * (up_movement ** max(m - trinomial_steps, 0)) * (down_movement ** max(trinomial_steps * 2 - trinomial_steps - m, 0))), 0)

    for k in range(trinomial_steps - 1, -1, -1):
        for m in range(0, 2 * k + 1):
            option_prices[(k, m)] = (probability_up * option_prices[(k + 1, m + 2)] + probability_middle * option_prices[(k + 1, m + 1)] + probability_down * option_prices[(k + 1, m)]) / discount_factor

    return option_prices[(0, 0)]


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.json
        underlying = data['underlying']
        df = fetch_historical_data(underlying, '90d') 
        S = get_spot_price(underlying)
        sigma = get_sigma(df)
        K = float(data['strike_price'])
        T = calculate_days_until_expiry(data['expiry_date']) / 252
        r = float(data['risk_free_rate']) / 100
        call_price_bs, put_price_bs, call_price_binomial, put_price_binomial, call_price_mc, put_price_mc, call_price_trinomial, put_price_trinomial = calculate_option_prices(S, K, T, r, sigma)
        response = {
            "callPriceBS": call_price_bs,
            "putPriceBS": put_price_bs,
            "callPriceBinomial": call_price_binomial,
            "putPriceBinomial": put_price_binomial,
            "callPriceMC": call_price_mc,
            "putPriceMC": put_price_mc,
            "callPriceTrinomial": call_price_trinomial,
            "putPriceTrinomial": put_price_trinomial,
            "HV": sigma*100
        }
        return jsonify(response)
    except Exception as e:
        print('Error:', e)
        return jsonify({"error": str(e)}), 500
    
def calculate_days_until_expiry(expiry_date):
    try:
        today = datetime.now().date()
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()  
        days_until_expiry = (expiry - today).days  
        return days_until_expiry
    except Exception as e:
        print("Error calculating days until expiry:", e)
        return None

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
