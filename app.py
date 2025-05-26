from flask import Flask, request, render_template
import requests

app = Flask(__name__)

# 국가 코드 → 통화 코드 매핑
CURRENCY_MAP = {
    "US": "USD",
    "KR": "KRW",
    "JP": "JPY",
    "CN": "CNY",
    "GB": "GBP",
    "EU": "EUR",
    "TH": "THB",
    "VN": "VND"
}

# 사용자 IP를 기반으로 국가 코드 가져오기
def get_user_country(ip):
    try:
        # 로컬 네트워크일 경우 외부 IP 요청
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

# 입력 금액을 원(KRW)으로 변환 (환율을 USD 기준으로 변환 후 KRW로 변환)
def convert_to_krw(amount, from_currency):
    try:
        # 만약 이미 KRW이면 변환 없이 그대로 반환
        if from_currency == "KRW":
            return int(amount)  # 정수로 변환하여 그대로 반환

        # USD 기준 환율 가져오기
        res = requests.get("https://api.frankfurter.app/latest?from=USD")
        data = res.json()

        print("[API 응답 확인]", data)  # 디버깅용 출력

        if "rates" not in data or "KRW" not in data["rates"]:
            print("[CONVERT ERROR] API 응답 없음")
            return 0
        
        usd_to_krw = data["rates"]["KRW"]
        
        # 다른 통화인 경우 먼저 USD로 변환 후 KRW로 변환
        res_currency = requests.get(f"https://api.frankfurter.app/latest?from={from_currency}")
        currency_data = res_currency.json()
        
        if "rates" not in currency_data or "USD" not in currency_data["rates"]:
            print("[CONVERT ERROR] 해당 통화 변환 없음")
            return 0

        from_currency_to_usd = currency_data["rates"]["USD"]
        converted_to_usd = amount * from_currency_to_usd
        return round(converted_to_usd * usd_to_krw)  # 정수 반올림
    except Exception as e:
        print("[CONVERT ERROR]", e)
        return 0

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

            # 숫자 검증 (소수 포함)
            if not input_price.replace(".", "", 1).isdigit():
                error_message = "유효한 숫자를 입력하세요."
            else:
                input_price = float(input_price)
                if input_price <= 0:
                    error_message = "금액은 0보다 커야 합니다."
                else:
                    converted_price = convert_to_krw(input_price, currency_code)
        except ValueError:
            error_message = "올바른 금액을 입력하세요."

    return render_template("index.html",
                           country=country_name,
                           currency=currency_code,
                           converted_price=converted_price,
                           input_price=input_price,
                           error_message=error_message)

if __name__ == "__main__":
    app.run(debug=True)