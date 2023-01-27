import os
from typing import Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st

CWD = os.getcwd()
url = "https://macrotrends-finance.p.rapidapi.com"

FIS = "statements/income"
FBS = "statements/balance"
FCS = "statements/cash"
# FKR = "financial-key-ratios"

DATAS = [FIS, FBS, FCS]

headers = {
    "X-RapidAPI-Host": "macrotrends-finance.p.rapidapi.com",
    "X-RapidAPI-Key": os.environ["API_KEY"],
}


nasdaq = pd.read_csv(f"{CWD}/nasdaq_screener_1650228647021.csv")[["Symbol", "Name"]]
nyse = pd.read_csv(f"{CWD}/NYSE.csv")[["Symbol", "Name"]]
all_stocks = pd.concat([nasdaq, nyse])

cols_df = pd.read_csv(f"{CWD}/cols_needed.csv")
use_cols = set(cols_df[cols_df["need"] == "y"].col.values)


@st.cache
def get_stock_info(sym: str) -> Optional[pd.DataFrame]:
    dfs = []
    for data in DATAS:
        params = {"freq": "Q", "symbol": sym.replace("/", ".")}
        data_res = requests.get(f"{url}/{data}", params=params, headers=headers)
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
    cols = [c for c in df_merged.columns if c in use_cols]
    return df_merged[cols]


symbols = all_stocks.Symbol.tolist()
symbols.remove("JPM")
symbols = ["JPM"] + symbols
sym = st.selectbox("Pick a stock", symbols)

st.write("You selected:\n", all_stocks[all_stocks["Symbol"] == sym])

st.write("Gathering Balance Sheet information...")


if sym:
    st.write(sym)

    df = get_stock_info(sym)
    if df is None:
        st.warning(f"It seems data for {sym} is not available. Try another stock.")
    else:

        st.download_button(
            "Download", df.to_csv(), f"{sym}.csv", "text/csv", key="download-csv"
        )
        st.write(df)

        # Line chart
        all_cols = df.columns
        viz = st.multiselect(
            "Pick a column to visualize", all_cols, default=all_cols[0]
        )

        line_data = df[viz]
        st.line_chart(line_data)
