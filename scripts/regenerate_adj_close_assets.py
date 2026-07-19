from pathlib import Path
import re

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SA_DIR = ROOT / "sa"
START = "2018-01-01"
END = "2026-07-01"


def download_adjusted_close(symbol: str) -> pd.DataFrame:
    frame = yf.download(symbol, start=START, end=END, auto_adjust=False, actions=False, progress=False)
    if frame is None or frame.empty:
        raise RuntimeError(f"No data returned for {symbol}")

    if isinstance(frame.columns, pd.MultiIndex):
        adj_close = frame.xs("Adj Close", axis=1, level=0)
        if isinstance(adj_close, pd.DataFrame):
            adj_close = adj_close.iloc[:, 0]
    else:
        adj_close = frame["Adj Close"]

    result = adj_close.rename("調整收盤價").reset_index()
    result.columns = ["日期", "調整收盤價"]
    result["日期"] = pd.to_datetime(result["日期"])
    return result.sort_values("日期").reset_index(drop=True)


def format_month_dates(series: pd.Series) -> pd.Series:
    return series.dt.year.astype(str) + "/" + series.dt.month.astype(str) + "/" + series.dt.day.astype(str)


def month_end_prices(frame: pd.DataFrame, output_name: str) -> pd.DataFrame:
    result = frame.groupby(frame["日期"].dt.to_period("M"), sort=True).tail(1).copy()
    result["日期"] = format_month_dates(result["日期"])
    result = result.rename(columns={"調整收盤價": output_name})
    return result.reset_index(drop=True)


def write_csv(frame: pd.DataFrame, path: Path, float_format: str | None = None) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format=float_format)


def csv_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def replace_js_template(text: str, variable_name: str, csv_text: str) -> str:
    pattern = rf"const {re.escape(variable_name)} = `.*?`;"
    replacement = f"const {variable_name} = `{csv_text}`;"
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Failed to replace JavaScript template literal: {variable_name}")
    return updated


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def update_dashboard(return_csv_text: str) -> None:
    path = SA_DIR / "monthly_return_dashboard.html"
    text = path.read_text(encoding="utf-8")
    text = replace_js_template(text, "csvText", return_csv_text)
    text = apply_replacements(
        text,
        [
            (
                "這份儀表板以月報酬率為主，從時間序列、分布、箱型圖、共同變動與類別統計五個角度比較 0050 與臺灣加權指數。\n        月報酬率公式為（本月月底價格 − 上月月底價格）／上月月底價格。",
                "這份儀表板以調整收盤價計算出的月報酬率為主，從時間序列、分布、箱型圖、共同變動與類別統計五個角度比較 0050 與臺灣加權指數。\n        月報酬率公式為（本月月底調整收盤價 − 上月月底調整收盤價）／上月月底調整收盤價。",
            ),
            (
                "這份儀表板以調整收盤價計算出的月報酬率為主，從時間序列、分布、箱型圖、共同變動與類別統計五個角度比較 0050 與臺灣加權指數。\n        月報酬率公式為（本月月底調整收盤價 − 上月月底調整收盤價）／上月月底調整收盤價。",
                "這份儀表板以調整收盤價計算出的月報酬率為主，從時間序列、分布、箱型圖、共同變動與類別統計五個角度比較 0050 與臺灣加權指數。\n        月報酬率公式為（本月月底調整收盤價 − 上月月底調整收盤價）／上月月底調整收盤價。",
            ),
        ],
    )
    path.write_text(text, encoding="utf-8")


def update_report(price_csv_text: str, return_csv_text: str) -> None:
    path = SA_DIR / "monthly_return_report.html"
    text = path.read_text(encoding="utf-8")
    text = replace_js_template(text, "priceCsv", price_csv_text)
    text = replace_js_template(text, "returnCsv", return_csv_text)
    text = apply_replacements(
        text,
        [
            (
                "本報告以每月最後一個交易日收盤價整理為月資料，再依前後月價格計算月報酬率。為避免把缺少前期基準值的資料誤納入統計，沒有前一個月底價格的月份不會計入月報酬率分析。",
                "本報告以每月最後一個交易日調整收盤價整理為月資料，再依前後月價格計算月報酬率。為避免把缺少前期基準值的資料誤納入統計，沒有前一個月底調整收盤價的月份不會計入月報酬率分析。",
            ),
            (
                "本報告以每月最後一個交易日調整收盤價整理為月資料，再依前後月價格計算月報酬率。為避免把缺少前期基準值的資料誤納入統計，沒有前一個月底調整收盤價的月份不會計入月報酬率分析。",
                "本報告以每月最後一個交易日調整收盤價整理為月資料，再依前後月調整收盤價計算月報酬率。為避免把缺少前期基準值的資料誤納入統計，沒有前一個月底調整收盤價的月份不會計入月報酬率分析。",
            ),
            (
                "本報告以每月最後一個交易日價格計算月報酬率，並用於描述統計與圖表分析。",
                "本報告以每月最後一個交易日調整收盤價計算月報酬率，並用於描述統計與圖表分析。",
            ),
            (
                "月價格資料共有 ",
                "月調整價格資料共有 ",
            ),
            (
                "因首月缺少前一期價格，月報酬率有效樣本為 ",
                "因首月缺少前一期調整收盤價，月報酬率有效樣本為 ",
            ),
            (
                "2018/1/31 沒有前一個月底價格，因此月報酬率留白並排除於統計之外；若未來新增資料出現缺漏，建議使用相同月份成對刪除方式。",
                "2018/1/31 沒有前一個月底調整收盤價，因此月報酬率留白並排除於統計之外；若未來新增資料出現缺漏，建議使用相同月份成對刪除方式。",
            ),
            (
                "['月底價格', '每月最後一個交易日的收盤價。若月底為週末或休市日，則改用該月最後交易日。', '作為月報酬率計算的基礎價格。']",
                "['月底調整收盤價', '每月最後一個交易日的調整收盤價。若月底為週末或休市日，則改用該月最後交易日。', '作為月報酬率計算的基礎價格。']",
            ),
            (
                "['月報酬率', '（本月月底價格 − 上月月底價格）／上月月底價格。', '用來比較兩資產的平均表現、波動與相關性。']",
                "['月報酬率', '（本月月底調整收盤價 − 上月月底調整收盤價）／上月月底調整收盤價。', '用來比較兩資產的平均表現、波動與相關性。']",
            ),
            (
                "以相鄰兩個月底價格計算月報酬率，因此首月只保留價格、不進入月報酬率統計。",
                "以相鄰兩個月底調整收盤價計算月報酬率，因此首月只保留價格、不進入月報酬率統計。",
            ),
            (
                "以相鄰兩個月底調整收盤價計算月報酬率，因此首月只保留價格、不進入月報酬率統計。",
                "以相鄰兩個月底調整收盤價計算月報酬率，因此首月只保留調整價格、不進入月報酬率統計。",
            ),
        ],
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    etf_daily = download_adjusted_close("0050.TW")
    index_daily = download_adjusted_close("^TWII")

    etf_daily_out = etf_daily.copy()
    index_daily_out = index_daily.copy()
    etf_daily_out["日期"] = etf_daily_out["日期"].dt.strftime("%Y-%m-%d")
    index_daily_out["日期"] = index_daily_out["日期"].dt.strftime("%Y-%m-%d")

    write_csv(etf_daily_out, DATA_DIR / "0050.csv", float_format="%.6f")
    write_csv(index_daily_out, DATA_DIR / "taiwan_weighted_index.csv", float_format="%.6f")

    etf_month = month_end_prices(etf_daily, "0050調整收盤價")
    index_month = month_end_prices(index_daily, "臺灣加權指數調整收盤價")

    merged = etf_month.merge(index_month, on="日期", how="inner")
    price_columns = ["0050調整收盤價", "臺灣加權指數調整收盤價"]
    merged[price_columns] = merged[price_columns].round(2)
    write_csv(merged, DATA_DIR / "0050_台灣加權指數_收盤價比較.csv", float_format="%.2f")

    returns = pd.DataFrame()
    returns["日期"] = merged["日期"]
    returns["0050月報酬率"] = merged["0050調整收盤價"].pct_change()
    returns["臺灣加權指數月報酬率"] = merged["臺灣加權指數調整收盤價"].pct_change()
    write_csv(returns, DATA_DIR / "0050_台灣加權指數_月報酬率比較.csv", float_format="%.6f")

    price_csv_text = csv_file_text(DATA_DIR / "0050_台灣加權指數_收盤價比較.csv")
    return_csv_text = csv_file_text(DATA_DIR / "0050_台灣加權指數_月報酬率比較.csv")

    update_dashboard(return_csv_text)
    update_report(price_csv_text, return_csv_text)

    print("Rebuilt adjusted-close CSV and HTML assets.")
    print((DATA_DIR / "0050.csv").name)
    print((DATA_DIR / "taiwan_weighted_index.csv").name)
    print((DATA_DIR / "0050_台灣加權指數_收盤價比較.csv").name)
    print((DATA_DIR / "0050_台灣加權指數_月報酬率比較.csv").name)
    print((SA_DIR / "monthly_return_dashboard.html").name)
    print((SA_DIR / "monthly_return_report.html").name)


if __name__ == "__main__":
    main()