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