# -*- coding: utf-8 -*-
"""
抓取證交所／櫃買開放資料，彙整成 data/stocks.json（給公開網頁讀取）。
由 GitHub Actions 每日排程執行；也可本機執行：python scripts/fetch_data.py
只用 Python 內建套件。
"""
import json, ssl, os, time, datetime, urllib.request

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

TWSE = "https://openapi.twse.com.tw/v1/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"
# 備援：證交所另一服務（openapi 對雲端 IP 軟封鎖時改用這個）
TWSE_RWD = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"

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

ERRORS = {}

def get(url, tries=3):
    """抓取並解析 JSON（任何型別），失敗回 None 並記錄原因。"""
    name = url.split("/")[-1].split("?")[0]
    last = ""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-TW,zh;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=60, context=_SSL) as r:
                raw = r.read().decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            print(f"  [warn] {name} 第{i+1}次失敗: {last}")
            time.sleep(2)
    ERRORS[name] = last
    print(f"  [FAIL] {name}: {last}")
    return None

def index(url, key):
    data = get(url)
    out = {}
    if isinstance(data, list):
        for row in data:
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

def ymd(s):
    s = str(s or "")
    return f"{s[:4]}/{s[4:6]}/{s[6:8]}" if len(s) == 8 else s

IND = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維",
    "05": "電機機械", "06": "電器電纜", "07": "化學生技醫療", "08": "玻璃陶瓷",
    "09": "造紙工業", "10": "鋼鐵工業", "11": "橡膠工業", "12": "汽車工業",
    "13": "電子工業", "14": "建材營造", "15": "航運業", "16": "觀光餐旅",
    "17": "金融保險業", "18": "貿易百貨", "19": "綜合", "20": "其他",
    "21": "化學工業", "22": "生技醫療業", "23": "油電燃氣業", "24": "半導體業",
    "25": "電腦及週邊設備業", "26": "光電業", "27": "通信網路業", "28": "電子零組件業",
    "29": "電子通路業", "30": "資訊服務業", "31": "其他電子業", "32": "文化創意業",
    "33": "農業科技業", "34": "電子商務", "35": "綠能環保", "36": "數位雲端",
    "37": "運動休閒", "38": "居家生活",
}
def ind(code):
    code = str(code or "").strip()
    return IND.get(code, f"產業代碼 {code}") if code else None

def cap_str(v):
    return f"{v/1e8:.2f} 億元" if v is not None else None

def twse_rwd_fallback():
    """openapi 上市全失敗時，改用 www.twse.com.tw/rwd 抓上市收盤/PE/殖利率/淨值比。"""
    today = datetime.date.today()
    for back in range(0, 8):
        d = today - datetime.timedelta(days=back)
        ds = d.strftime("%Y%m%d")
        data = get(f"{TWSE_RWD}?date={ds}&selectType=ALL&response=json")
        if isinstance(data, dict) and data.get("data"):
            rows = {}
            for r in data["data"]:
                code = str(r[0]).strip()
                # 欄位：證券代號,證券名稱,收盤價,殖利率,股利年度,本益比,股價淨值比
                rows[code] = {"name": r[1], "close": r[2], "yield": r[3],
                              "pe": r[5], "pb": r[6], "date": ymd(ds)}
            print(f"  備援成功：{ds} 取得上市 {len(rows)} 檔")
            return rows
    return {}

def main():
    print("抓取上市（openapi）…")
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

    tw_codes = set(twQuote) | set(twBwibbu) | set(twBasic)
    if tw_codes:
        for code in tw_codes:
            q = twQuote.get(code, {}); b = twBwibbu.get(code, {})
            f = twIncome.get(code, {}); bs = twBasic.get(code, {})
            qf = twQfii.get(code)
            close = fnum(q.get("ClosingPrice")); pb = fnum(b.get("PBratio"))
            gm = f.get("毛利率(%)(營業毛利)/(營業收入)")
            stocks[code] = {
                "name": q.get("Name") or b.get("Name") or bs.get("公司名稱", ""),
                "market": "上市", "date": roc(q.get("Date")),
                "close": close, "pe": b.get("PEratio") or None,
                "yield": b.get("DividendYield") or None, "pb": b.get("PBratio") or None,
                "bvps": round(close/pb, 2) if (close is not None and pb) else None,
                "gm": gm or None,
                "gm_season": f"{f.get('年度')}年第{f.get('季別')}季" if f.get("年度") else "",
                "capital": cap_str(fnum(bs.get("實收資本額"))),
                "foreign": qf.get("SharesHeldPer") if qf else None,
                "industry": ind(bs.get("產業別")),
                "chairman": bs.get("董事長") or None, "manager": bs.get("總經理") or None,
                "founded": ymd(bs.get("成立日期")), "listed": ymd(bs.get("上市日期")),
                "web": bs.get("網址") or None, "addr": bs.get("住址") or None,
            }
    else:
        print("  openapi 上市全失敗，改用 www.twse.com.tw/rwd 備援…")
        for code, r in twse_rwd_fallback().items():
            close = fnum(r["close"]); pb = fnum(r["pb"])
            stocks[code] = {
                "name": r["name"], "market": "上市", "date": r["date"],
                "close": close, "pe": (r["pe"] if r["pe"] not in ("", "0.00", None) else None),
                "yield": r["yield"] or None, "pb": r["pb"] or None,
                "bvps": round(close/pb, 2) if (close is not None and pb) else None,
                "gm": None, "gm_season": "", "capital": None, "foreign": None,
                "industry": None, "chairman": None, "manager": None,
                "founded": "", "listed": "", "web": None, "addr": None,
            }

    tp_codes = set(tpQuote) | set(tpPera) | set(tpBasic)
    for code in tp_codes:
        q = tpQuote.get(code, {}); p = tpPera.get(code, {})
        f = tpIncome.get(code, {}); bs = tpBasic.get(code, {})
        qf = tpQfii.get(code, {})
        close = fnum(q.get("Close")); pb = fnum(p.get("PriceBookRatio"))
        rev = fnum(f.get("營業收入")); gross = fnum(f.get("營業毛利（毛損）"))
        gm = f"{gross/rev*100:.2f}" if (rev and gross is not None) else None
        cap = fnum(bs.get("Paidin.Capital.NTDollars")) or fnum(q.get("Capitals"))
        fr = qf.get("PercentageOfSharesOC/FMIHeld")
        stocks[code] = {
            "name": q.get("CompanyName") or bs.get("CompanyName", ""),
            "market": "上櫃", "date": roc(q.get("Date")),
            "close": close, "pe": p.get("PriceEarningRatio") or None,
            "yield": p.get("YieldRatio") or None, "pb": p.get("PriceBookRatio") or None,
            "bvps": round(close/pb, 2) if (close is not None and pb) else None,
            "gm": gm, "gm_season": f"{f.get('Year')}年第{f.get('Season')}季" if f.get("Year") else "",
            "capital": cap_str(cap), "foreign": fr.replace("%", "") if fr else None,
            "industry": ind(bs.get("SecuritiesIndustryCode")),
            "chairman": bs.get("Chairman") or None, "manager": bs.get("GeneralManager") or None,
            "founded": ymd(bs.get("DateOfIncorporation")), "listed": ymd(bs.get("DateOfListing")),
            "web": bs.get("WebAddress") or None, "addr": bs.get("Address") or None,
        }

    twse_n = sum(1 for v in stocks.values() if v["market"] == "上市")
    tpex_n = sum(1 for v in stocks.values() if v["market"] == "上櫃")

    os.makedirs("data", exist_ok=True)
    with open("data/stocks.json", "w", encoding="utf-8") as fp:
        json.dump(stocks, fp, ensure_ascii=False, separators=(",", ":"))

    meta = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(stocks), "twse_count": twse_n, "tpex_count": tpex_n,
        "twse_date": next((v["date"] for v in stocks.values() if v["market"] == "上市" and v["date"]), ""),
        "tpex_date": next((v["date"] for v in stocks.values() if v["market"] == "上櫃" and v["date"]), ""),
        "errors": ERRORS,
    }
    with open("data/meta.json", "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)

    print(f"完成：上市 {twse_n}、上櫃 {tpex_n}，共 {len(stocks)} 檔")
    if ERRORS:
        print("失敗來源：", ERRORS)

if __name__ == "__main__":
    main()
