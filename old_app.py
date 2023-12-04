import json
import os
from typing import Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
import base64
from datetime import datetime, timedelta


# Fun background stuff 
# from PIL import Image
# import io
#st.title("👋🏻 It's almost Ma's birthday. Did you get your wine and ice cream?")
st.title("🤖 Think-O-Meter Inc.")
# background_image = "birthday.webp"
# image = Image.open(background_image)
# opacity = 85  # 128 is 50%
# image.putalpha(opacity)
# buffered = io.BytesIO()
# image.save(buffered, format='PNG')

# st.markdown(
#     f"""
#     <style>
#     .stApp {{
        
#         background: url(data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()});
#         background-size: cover;
#     }}
#     </style>
#     """,
#     unsafe_allow_html=True
# )


# Actual app
CWD = os.getcwd()
url = "https://macrotrends-finance.p.rapidapi.com"

FIS = "statements/income"
FBS = "statements/balance"
FCS = "statements/cash"
PRICES = "quotes/history-price"

DATAS = [FIS, FBS, FCS]#, PRICES]

headers = {
    "X-RapidAPI-Host": "macrotrends-finance.p.rapidapi.com",
    "X-RapidAPI-Key": os.environ["API_KEY"],
}


nasdaq = pd.read_csv(f"{CWD}/nasdaq_screener_1650228647021.csv")[["Symbol", "Name"]]
nyse = pd.read_csv(f"{CWD}/NYSE.csv")[["Symbol", "Name"]]
all_stocks = pd.concat([nasdaq, nyse])

with open("col_order.json") as f:
    col_order = json.load(f)
cols_df = pd.read_csv(f"{CWD}/cols_needed.csv")
use_cols = set(cols_df[cols_df["need"] == "y"].col.values)


def to_friday(row):
    """Convert weekend to friday for matching with price history"""
    dt = datetime.strptime(row, '%Y-%m-%d')
    weekday = dt.weekday()
    if weekday == 6:
        dt = dt - timedelta(days=2)
    elif weekday == 5:
        dt = dt - timedelta(days=1)
    return dt.strftime('%Y-%m-%d')


@st.cache_data(persist=False)
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
    price_params = {"symbol": sym.replace("/", "."), "range":'15y'}
    data_res = requests.get(f"{url}/{PRICES}", params=price_params, headers=headers)
    if data_res.status_code == 200:
        df_prices = pd.DataFrame(data_res.json()).set_index("Date")
        # Some reports come on the weekend. Move to friday so we can merge with 
        # the closing dates
        df_merged.index = df_merged.index.map(to_friday)
        df_merged = df_merged.merge(df_prices, left_index=True, right_index=True, how="left")
    cols = [c for c in col_order if c in df_merged.columns and c in use_cols]
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
