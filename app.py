
import streamlit as st
from typing import Optional
import pandas as pd
import requests
import os

CWD = os.getcwd()
url = "https://macrotrends-finance.p.rapidapi.com"

FKR = "financial-key-ratios"
FCS = "financial-cash-statement"
FBS = "financial-balance-sheet"
FIS = "financial-income-statement"

headers = {
    "X-RapidAPI-Host": "macrotrends-finance.p.rapidapi.com",
    "X-RapidAPI-Key": os.environ["API_KEY"]
}


nasdaq = pd.read_csv(f"{CWD}/nasdaq_screener_1650228647021.csv")[["Symbol", "Name"]]
nyse = pd.read_csv(f"{CWD}/NYSE.csv")[["Symbol", "Name"]]
all_stocks = pd.concat([nasdaq, nyse])


@st.cache
def get_stock_info(sym: str, data: str) -> Optional[pd.DataFrame]:
    data_res = requests.get(f"{url}/{data}/{sym.replace('/','.')}", headers=headers)
    if data_res.status_code != 200:
        return
    return pd.DataFrame(data_res.json())


sym = st.selectbox(
    'Pick a stock',
    all_stocks.Symbol.tolist()
)

st.write('You selected:\n', all_stocks[all_stocks["Symbol"]==sym])

st.write("Gathering Balance Sheet information...")


if sym:
    st.write(sym)
    data = st.selectbox(
        'What data would you like?',
        [FBS, FKR, FCS, FIS]
    )
    df = get_stock_info(sym, data)
    if df is None:
        st.warning(f"It seems {data} for {sym} is not available. Try another stock.")
    else:
        for c, dt in zip(list(df.columns), df.dtypes):
            if dt == "object":
                df = df.drop(columns=[c])

        st.download_button(
           "Download",
           df.to_csv(),
           f"{sym}_{data}.csv",
           "text/csv",
           key='download-csv'
        )
        st.write(df)
