from flask import Flask, request, render_template
import requests

app = Flask(__name__)

# 국가 코드 → 통화 코드 매핑
CURRENCY_MAP = {
    "US": "USD",
    "KR": "KRW",
    "JP": "JPY",
    "GB": "GBP",
    "EU": "EUR",
    "FR": "EUR",
    "TH": "THB",
    "VN": "VND",
    "AU": "AUD",  # 호주
    "SG": "SGD"   # 싱가포르
}

# 사용자 IP를 기반으로 국가 코드 가져오기
def get_user_country(ip):
    try:
        if ip == "127.0.0.1" or ip.startswith("192.168."):
            ip = requests.get("https://api.ipify.org").text
        res = requests.get(f"http://ip-api.com/json/{ip}")
        data = res.json()
        if data.get("status") == "fail":
            print("[IP API ERROR] 위치 조회 실패")
            return "US", "United States"
        return data.get("countryCode", "US"), data.get("country", "United States")
    except Exception as e:
        print("[IP ERROR]", e)
        return "US", "United States"

# 국가 코드 → 통화 코드 변환
def get_currency_code(country_code):
    return CURRENCY_MAP.get(country_code, "USD")

# 입력 금액을 원(KRW)으로 변환
def convert_to_krw(amount, from_currency):
    try:
        if from_currency == "KRW":
            return int(amount)

        res = requests.get(f"https://api.exchangerate.host/latest?base={from_currency}", timeout=3)
        if res.status_code != 200:
            raise Exception("환율 API 요청 실패")

        data = res.json()
        print("[API 응답 확인]", data)

        if "rates" not in data or "KRW" not in data["rates"]:
            raise Exception("환율 정보 없음")

        currency_to_krw = data["rates"]["KRW"]
        return round(amount * currency_to_krw)
    except Exception as e:
        print("[CONVERT ERROR]", e)

        # 예외 대비 기본 환율
        fallback_rates = {
            "USD": 1300,
            "EUR": 1470,
            "JPY": 9.0,
            "GBP": 1650,
            "THB": 37,
            "VND": 0.053,
            "AUD": 880,
            "SGD": 980
        }

        rate = fallback_rates.get(from_currency)
        if rate:
            return round(amount * rate)
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    country_code, country_name = get_user_country(user_ip)
    currency_code = get_currency_code(country_code)

    converted_price = None
    input_price = None
    error_message = None

    if request.method == "POST":
        try:
            input_price = request.form.get("price", "0").strip()

            try:
                input_price = float(input_price)
                if input_price <= 0:
                    error_message = "금액은 0보다 커야 합니다."
                else:
                    converted_price = convert_to_krw(input_price, currency_code)
                    if converted_price is None:
                        error_message = f"{currency_code} → KRW 환율 정보를 불러올 수 없습니다."
            except ValueError:
                error_message = "유효한 숫자를 입력하세요."
        except Exception as e:
            error_message = "올바른 입력값을 제공하세요."

    return render_template("index.html",
                           country=country_name,
                           currency=currency_code,
                           converted_price=converted_price,
                           input_price=input_price,
                           error_message=error_message)

if __name__ == "__main__":
    app.run(debug=True)
