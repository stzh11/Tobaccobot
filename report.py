#!/usr/bin/env python3
"""
Пересчитывает все отчёты и пишет их в Google Sheets.
"""
import datetime as dt
import pandas as pd, gspread
from google.oauth2.service_account import Credentials

# --- настройки ---------------------------------------
GSHEET_ID = "1ohRzvfBFLlfXAOvvLqMP48Fa2hl30bO00JxydnVEXrU"
SERVICE_ACCOUNT_JSON = {'key': 1
}          # ваш dict

# --- авторизация -------------------------------------
scopes = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds  = Credentials.from_service_account_info(SERVICE_ACCOUNT_JSON, scopes=scopes)
gc     = gspread.authorize(creds)
sh     = gc.open_by_key(GSHEET_ID)

raw_ws  = sh.worksheet("Сырые ответы")
color_ws= sh.worksheet("Справочник цветов")

# --- читаем данные -----------------------------------
data  = pd.DataFrame(raw_ws.get_all_values()[1:])   # без заголовка
hdr   = raw_ws.row_values(1)
data.columns = hdr

# конвертируем типы
data['date'] = pd.to_datetime(data['date'], format="%Y-%m-%d %H:%M:%S")
for col in hdr[3:]:                # оценки
    data[col] = pd.to_numeric(data[col], errors='coerce')

# справочник
color_map = dict(color_ws.get_all_values()[1:])     # {group: color}

# --- удобные даты ------------------------------------
today     = dt.date.today()
week_ago  = today - dt.timedelta(days=7)
month_ago = today - dt.timedelta(days=30)

def slice_df(since):
    return data[data["date"].dt.date >= since]

# ============ 1. среднее по цветам ===================
def color_avg(df):
    melt = df.melt(id_vars=['shop','date'], var_name='group', value_name='rate')
    melt['color'] = melt['group'].map(color_map)
    return melt.groupby('color')['rate'].mean().reset_index()

week_color  = color_avg(slice_df(week_ago))
month_color = color_avg(slice_df(month_ago))

# пишем в лист
def to_sheet(df: pd.DataFrame, title: str):
    # NaN → ""  (или .fillna(0) если нужны нули)
    clean = df.round(2).fillna("").astype(str)

    try:
        ws = sh.worksheet(title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title, rows=200, cols=20)

    ws.update([clean.columns.tolist()] + clean.values.tolist())

# ============ 2. среднее по группам ==================
def group_week(df):
    current = df.mean(numeric_only=True).T.to_frame('this')
    prev    = slice_df(week_ago - dt.timedelta(days=7))\
              .query("date.dt.date < @week_ago")\
              .mean(numeric_only=True).T.to_frame('prev')
    res = current.join(prev)
    res['delta_%'] = (res['this'] - res['prev'])/res['prev']*100
    res = res.reset_index().rename(columns={'index':'group'})
    return res

to_sheet(group_week(slice_df(week_ago)), "Отчёт-Группы")

# ============ 3. среднее по магазинам / сети =========
def shop_week(df):
    shop = df.groupby('shop').mean(numeric_only=True).mean(axis=1)
    net  = pd.Series({'Сеть': df.mean(numeric_only=True).mean().round(2)})
    cur  = pd.concat([shop, net]).to_frame('this')
    prev = shop_week(slice_df(week_ago - dt.timedelta(days=7))) if 'prev_run' in globals() else cur
    res  = cur.join(prev.rename(columns={'this':'prev'}))
    res['delta_%'] = (res['this'] - res['prev'])/res['prev']*100
    res = res.reset_index().rename(columns={'index':'shop'})
    return res

to_sheet(shop_week(slice_df(week_ago)), "Отчёт-Магазины")

print("✅ отчёты пересчитаны")
