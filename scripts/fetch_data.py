# -*- coding: utf-8 -*-
"""
抓取證交所／櫃買開放資料，彙整成 data/stocks.json（給公開網頁讀取）。
由 GitHub Actions 每日排程執行；也可本機執行：python scripts/fetch_data.py
只用 Python 內建套件。
"""
import json, ssl, os, datetime, urllib.request

# 交易所憑證在新版 Python 下會驗證失敗，公開唯讀資料故略過驗證
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

TWSE = "https://openapi.twse.com.tw/v1/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"
EP = {
    "twQuote":  TWSE + "exchangeReport/STOCK_DAY_ALL",
    "twBwibbu": TWSE + "exchangeReport/BWIBBU_ALL",
    "twIncome": TWSE + "opendata/t187ap17_L",
    "twBasic":  TWSE + "opendata/t187ap03_L",
    "twQfii":   TWSE + "fund/MI_QFIIS_sort_20",
    "tpQuote":  TPEX + "tpex_mainboard_quotes",
    "tpPera":   TPEX + "tpex_mainboard_peratio_analysis",
    "tpIncome": TPEX + "mopsfin_t187ap06_O_ci",
    "tpBasic":  TPEX + "mopsfin_t187ap03_O",
    "tpQfii":   TPEX + "tpex_3insti_qfii",
}

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=40, context=_SSL) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  [warn] {url.split('/')[-1]} 失敗: {e}")
        return []

def index(url, key):
    out = {}
    for row in fetch(url):
        k = str(row.get(key, "")).strip()
        if k and k not in out:
            out[k] = row
    return out

def fnum(v):
    if v is None:
        return None
    s = str(v).replace(",", "").replace("%", "").strip()
    if s in ("", "--", "N/A", "不適用"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def roc(s):
    s = str(s or "")
    return f"{int(s[:3])+1911}/{s[3:5]}/{s[5:7]}" if len(s) == 7 else s

def cap_str(v):
    return f"{v/1e8:.2f} 億元" if v is not None else None

def main():
    print("抓取上市…")
    twQuote = index(EP["twQuote"], "Code")
    twBwibbu = index(EP["twBwibbu"], "Code")
    twIncome = index(EP["twIncome"], "公司代號")
    twBasic = index(EP["twBasic"], "公司代號")
    twQfii = index(EP["twQfii"], "Code")

    print("抓取上櫃…")
    tpQuote = index(EP["tpQuote"], "SecuritiesCompanyCode")
    tpPera = index(EP["tpPera"], "SecuritiesCompanyCode")
    tpIncome = index(EP["tpIncome"], "SecuritiesCompanyCode")
    tpBasic = index(EP["tpBasic"], "SecuritiesCompanyCode")
    tpQfii = index(EP["tpQfii"], "SecuritiesCompanyCode")

    stocks = {}

    for code, q in twQuote.items():
        b = twBwibbu.get(code, {}); f = twIncome.get(code, {})
        bs = twBasic.get(code, {}); qf = twQfii.get(code)
        close = fnum(q.get("ClosingPrice")); pb = fnum(b.get("PBratio"))
        gm = f.get("毛利率(%)(營業毛利)/(營業收入)")
        stocks[code] = {
            "name": q.get("Name", ""), "market": "上市",
            "date": roc(q.get("Date")),
            "close": close,
            "pe": b.get("PEratio") or None,
            "yield": b.get("DividendYield") or None,
            "pb": b.get("PBratio") or None,
            "bvps": round(close/pb, 2) if (close is not None and pb) else None,
            "gm": gm or None,
            "gm_season": f"{f.get('年度')}年第{f.get('季別')}季" if f.get("年度") else "",
            "capital": cap_str(fnum(bs.get("實收資本額"))),
            "foreign": qf.get("SharesHeldPer") if qf else None,
        }

    for code, q in tpQuote.items():
        p = tpPera.get(code, {}); f = tpIncome.get(code, {})
        bs = tpBasic.get(code, {}); qf = tpQfii.get(code, {})
        close = fnum(q.get("Close")); pb = fnum(p.get("PriceBookRatio"))
        rev = fnum(f.get("營業收入")); gross = fnum(f.get("營業毛利（毛損）"))
        gm = f"{gross/rev*100:.2f}" if (rev and gross is not None) else None
        cap = fnum(bs.get("Paidin.Capital.NTDollars")) or fnum(q.get("Capitals"))
        fr = qf.get("PercentageOfSharesOC/FMIHeld")
        stocks[code] = {
            "name": q.get("CompanyName", ""), "market": "上櫃",
            "date": roc(q.get("Date")),
            "close": close,
            "pe": p.get("PriceEarningRatio") or None,
            "yield": p.get("YieldRatio") or None,
            "pb": p.get("PriceBookRatio") or None,
            "bvps": round(close/pb, 2) if (close is not None and pb) else None,
            "gm": gm,
            "gm_season": f"{f.get('Year')}年第{f.get('Season')}季" if f.get("Year") else "",
            "capital": cap_str(cap),
            "foreign": fr.replace("%", "") if fr else None,
        }

    os.makedirs("data", exist_ok=True)
    with open("data/stocks.json", "w", encoding="utf-8") as fp:
        json.dump(stocks, fp, ensure_ascii=False, separators=(",", ":"))

    meta = {
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(stocks),
        "twse_date": next((v["date"] for v in stocks.values() if v["market"] == "上市"), ""),
        "tpex_date": next((v["date"] for v in stocks.values() if v["market"] == "上櫃"), ""),
    }
    with open("data/meta.json", "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)

    print(f"完成：{len(stocks)} 檔，已寫入 data/stocks.json")

if __name__ == "__main__":
    main()
