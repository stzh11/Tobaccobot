#!/usr/bin/env python3
import gspread
from gspread_formatting import CellFormat, Color, format_cell_ranges
from google.oauth2.service_account import Credentials

# --- ваши константы (скопируйте из main.py) -----------
GSHEET_ID = "1eDnLS60_u0gdaACKgWSG2a-CzYNWBDHdwJR9ataYjg8"
SERVICE_ACCOUNT_JSON = { 'key': 1}          # (ваш dict)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_JSON, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(GSHEET_ID)

# --- читаем справочник -------------------------------
color_ws = sh.worksheet("Справочник цветов")
rows     = color_ws.get_all_values()[1:]        # пропускаем заголовок
groups_by_color = {}
for g, c in rows:
    groups_by_color.setdefault(c.strip(), []).append(g.strip())

# --- вычисляем столбцы для каждой группы -------------
raw_ws = sh.worksheet("Сырые ответы")
header = raw_ws.row_values(1)                   # заголовок
ranges  = []                                    # (A2:A, C2:C, …)

def col2a(n):                                   # 1 -> A
    s=""; n-=1
    while n>=0:
        s=chr(n%26+65)+s; n=n//26-1
    return s

for idx, name in enumerate(header, start=1):
    for color, groups in groups_by_color.items():
        if name.strip() in groups:
            col_letter = col2a(idx)
            rng = f"{col_letter}2:{col_letter}"   # без огранич. вниз
            ranges.append((rng, color))

# --- применяем формат --------------------------------
fmt = {
    "Жёлтый": CellFormat(backgroundColor=Color(1,1,0.6)),
    "Зелёный": CellFormat(backgroundColor=Color(0.7,1,0.7)),
}

# объединяем по цвету
apply = [(r, fmt[c]) for r, c in ranges]
format_cell_ranges(raw_ws, apply)

print("✅ Цветовое форматирование установлено")
