import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from mpl_toolkits.mplot3d import Axes3D
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

plt.style.use("dark_background")

class LiveSurfaceApp(EClient, EWrapper):

    def __init__(self):
        EClient.__init__(self, self)
        self.iv_dict = {}
        self.id_map = {}
        self.expirations = []
        self.strikes = []
        self.spot_price = -1
        self.underlying_conId = 0
        self.resolved = threading.Event()
        self.chain_resolved = threading.Event()

    def connectAck(self):
        print("TWS Acknowledged Connection")

    def error(self, reqId, errorCode, errorString):
        #2104, 2106, and 2108 are notifications, can be safely ignored
        if errorCode not in [2104, 2106, 2108]:
            print(reqId, errorCode, errorString)

    #Handles the contract details for the underlying
    def contractDetails(self, reqId, contractDetails):
        self.underlying_conId = contractDetails.contract.conId
        self.resolved.set()

    #Gets spot price
    def tickPrice(self, reqId, tickType, price, attrib):
        if reqId == 999 and tickType in [4, 9] and price > 0:
            self.spot_price = price

    #Receives strikes and expirations for the contract that you are using
    def securityDefinitionOptionParameter(self, reqId, exchange, underlyingConId, tradingClass, multiplier, expirations, strikes):
        if exchange == 'SMART':
            self.expirations = sorted(list(expirations))
            self.strikes = sorted(list(strikes))
            self.chain_resolved.set()
    
    def tickOptionComputation(self, reqId, tickType, tickAttrib, impliedVol, delta, optPrice, pvDivedend, gamma, vega, theta, undPrice):
        if tickType == 13 and impliedVol is not None:
            self.iv_dict[reqId] = impliedVol


def run_loop(app):
    app.run()

def start_app(symbol="SPY"):
    app = LiveSurfaceApp()
    app.connect('127.0.0.1', 7497, clientId=1)

    api_thread = threading.Thread(target=run_loop, args = (app, ), daemon=True)
    api_thread.start()
    time.sleep(1)

    underlying = Contract()
    underlying.symbol = symbol
    underlying.security = 'STK'
    underlying.exchange = 'SMART'
    underlying.currency = 'USD'

    app.reqContractDetails(1, underlying)
    app.resolve.wait(timeout = 5)
    
    #This number should be set to the reqId number you set up in tickPrice(), gets the mkt data (spot price) for the
    app.reqMktData(999, underlying, "", False, False, [])
    while app.spot_price == -1: time.sleep(.1)
    spot = app.spot_price

    app.reqSecDefOptParams(2, symbol, "", "STK", app.underlying_conId)
    app.chain_resolved.wait(timeout=5)

    today = time.strftime("%Y%m%d")
    target_exps = [e for e in app.expirations if e >= today][:6]
    target_strikes = [s for s in app.strikes if spot *.98 <= s <= spot *1.02]

    req_id = 1000
    #Creates the live data streams for the options contracts that we requested directly above in target_exps and target_strikes
    for exp in target_exps:
        for strike in target_strikes:
            opt = Contract()
            opt.symbol = symbol
            opt.secType = 'OPT'
            opt.exchange = 'SMART'
            opt.currency = 'USD'
            opt.lastTradeDateOrContractMonth = exp
            opt.strike = strike
            opt.right = 'C' if strike >= spot else 'P'
            app.id_map[req_id] = (exp, strike)

            app.reqMktData(req_id, opt, "106", False, False, [])
            req_id += 1
            time.sleep(.1)
    return app



