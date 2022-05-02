
import streamlit as st
from typing import Optional
import pandas as pd
import requests
import os
import numpy as np

CWD = os.getcwd()
url = "https://macrotrends-finance.p.rapidapi.com"

FIS = "income-statement"
FBS = "balance-statement"
FCS = "financial-cash-statement"
FKR = "financial-key-ratios"

DATAS = [FIS, FBS, FCS, FKR]

headers = {
    "X-RapidAPI-Host": "macrotrends-finance.p.rapidapi.com",
    "X-RapidAPI-Key": os.environ["API_KEY"]
}


nasdaq = pd.read_csv(f"{CWD}/nasdaq_screener_1650228647021.csv")[["Symbol", "Name"]]
nyse = pd.read_csv(f"{CWD}/NYSE.csv")[["Symbol", "Name"]]
all_stocks = pd.concat([nasdaq, nyse])


@st.cache
def get_stock_info(sym: str) -> Optional[pd.DataFrame]:
    dfs = []
    for data in DATAS:
        data_res = requests.get(f"{url}/{data}/{sym.replace('/','.')}?freq=Q", headers=headers)
        if data_res.status_code != 200:
            continue
        df = pd.DataFrame(data_res.json())
        for c, dt in zip(list(df.columns), df.dtypes):
            if dt == "object":
                df[c] = df[c].replace("", np.nan)
        dfs.append(df)
    
    df_merged = None
    for df in dfs:
        if df_merged is None:
            df_merged = df
        else:
            df_merged = df_merged.merge(df, left_index=True, right_index=True)
    return df_merged


symbols = all_stocks.Symbol.tolist()
symbols.remove("JPM")
symbols = ["JPM"] + symbols
sym = st.selectbox(
    'Pick a stock',
    symbols
)

st.write('You selected:\n', all_stocks[all_stocks["Symbol"]==sym])

st.write("Gathering Balance Sheet information...")


if sym:
    st.write(sym)

    df = get_stock_info(sym)
    if df is None:
        st.warning(f"It seems data for {sym} is not available. Try another stock.")
    else:

        st.download_button(
           "Download",
           df.to_csv(),
           f"{sym}.csv",
           "text/csv",
           key='download-csv'
        )
        st.write(df)
        
        # Line chart
        all_cols = df.columns
        viz = st.multiselect("Pick a column to visualize", all_cols, default=all_cols[0])

        line_data = df[viz]
        st.line_chart(line_data)
        
