import json
import os
from typing import Optional
import shutil
import sys

import numpy as np
import pandas as pd
import requests
import streamlit as st
import base64
from datetime import datetime, timedelta
from selenium import webdriver
import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import Optional
from time import sleep
from seleniumbase import Driver

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait


# Fun background stuff 
# from PIL import Image
# import io
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
# Reload the tickers (symbols.json)
# ticker_url = "https://www.macrotrends.net/assets/php/ticker_search_list.php?_=1701641275073"
# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
# }
# ticker_data = requests.get(ticker_url, headers=headers)


LINKS = {
    "https://www.macrotrends.net/stocks/charts/{symbol}/balance-sheet?freq=Q": "balance_sheet",
    "https://www.macrotrends.net/stocks/charts/{symbol}/cash-flow-statement?freq=Q": "cash_flow",
    "https://www.macrotrends.net/stocks/charts/{symbol}/income-statement?freq=Q": "income_statement"
}
with open("symbols.json", "r") as f:
    SYMBOLS = json.load(f)

with open("macrotrends_to_cols.json", "r") as f:
    COL_MAPPER = json.load(f)


with open("col_order.json") as f:
    COL_ORDER = json.load(f)


COLS_DF = pd.read_csv(f"{CWD}/cols_needed.csv")
USE_COLS = set(COLS_DF[COLS_DF["need"] == "y"].col.values)
# DRIVER = Driver(uc=True, headless=True)


def extract_a_tag(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, 'html.parser')
        return soup.a.text
    except AttributeError:
        return None



# @st.cache_resource 
# def get_driver():
#     os.system("rm -rf chromedriver-linux64.zip chromedriver-linux64")
#     os.system("wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/119.0.6045.105/linux64/chromedriver-linux64.zip")
#     os.system("unzip chromedriver-linux64.zip")
#     print("HERE")
#     sys.path.append(f"{os.getcwd()}/chromedriver-linux64/chromedriver")
#     # os.system("ln -s chromedriver-linux64/chromedriver /home/adminuser/venv/bin/chromedriver")
#     # os.system('sbase install chromedriver -p')
#     # os.system('ln -s /usr/local/bin/chromedriver /home/appuser/venv/bin/chromedriver')
#     # os.system('ln -s /home/appuser/venv/lib/python3.7/site-packages/seleniumbase/drivers/geckodriver /home/appuser/venv/bin/geckodriver')
#     return Driver(browser="chrome", uc=True, headless=True)#, binary_location=get_chromedriver_path())
#     # return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


@st.cache_resource(show_spinner=False)
def get_chromedriver_path():
    return shutil.which('chromedriver')


@st.cache_resource(show_spinner=False)
def get_webdriver_options():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-features=NetworkService")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-features=VizDisplayCompositor")
    return options


def get_webdriver_service():
    service = Service(
        executable_path=get_chromedriver_path()
    )
    return service


@st.cache_data(persist=False)
def get_stock_info(sym: str) -> Optional[pd.DataFrame]:
    print("Getting stock info")
    progress_text = f"Loading data for {sym}. Please wait."
    progress = 0
    progress_bar = st.progress(0, text=progress_text) 
    dfs = []
    st.write("Getting driver")
    # DRIVER = get_driver()
    DRIVER = webdriver.Chrome(options=get_webdriver_options(), service=get_webdriver_service())
    st.write(f"Got driver! {DRIVER}")
    for link, data_type in LINKS.items():
        st.write(f"Getting {data_type}")
        progress_text = f"Loading {data_type.replace('_', ' ')} for {sym}. Please wait."
        progress_bar.progress(progress, text=progress_text)
        print("Getting", data_type)
        DRIVER.get(link.format(symbol=sym))
        print("Sleeping for 3")
        sleep(3)
        print("Awake")
        html_content = DRIVER.page_source
        json_match = re.search(r'var originalData = \[(.*?)\];', html_content, re.DOTALL)
        print("Looking for table data")
        if not json_match:
            print("Couldn't find it")
            continue
        print("Found it!")
        progress += 15
        progress_bar.progress(progress, text=progress_text)
        data = json.loads(f"[{json_match.group(1)}]")
        print("Loaded json")
        df = pd.DataFrame(data)
        if 'popup_icon' in df.columns:
            df.pop('popup_icon')
        print("Got DF")
        df["field_name"] = df['field_name'].apply(extract_a_tag)
        df = df.dropna(subset=['field_name'])
        df = df.set_index("field_name").T
        df = df.rename_axis("Date")
        dfs.append(df)
        print("Added", data_type)
        progress += 15
        progress_bar.progress(progress, text=progress_text)
    print("Done with loop")
    if not dfs:
        st.warning(str(shutil.which("chromedriver")))
        return
    df_merged = dfs[0]
    for df_ in dfs[1:]:
        df_merged = df_merged.merge(df_, left_index=True, right_index=True)
    df_merged = df_merged.rename(columns=COL_MAPPER)
    cols = [c for c in COL_ORDER if c in df_merged.columns and c in USE_COLS]
    df_merged = df_merged.fillna(np.nan)
    for c in df_merged.columns:
        df_merged.loc[df_merged[c]=="", c] = np.nan
        df_merged[c] = df_merged[c].astype(float)
    progress_bar.progress(100)
    return df_merged
    


SYMBOLS.remove("JPM/jpmorgan-chase")
SYMBOLS = ["JPM/jpmorgan-chase"] + SYMBOLS
sym = st.selectbox("Pick a stock", SYMBOLS)

st.write("You selected:\n", sym)


if sym:
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
