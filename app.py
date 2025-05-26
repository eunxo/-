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
    "FR": "EUR",  # 프랑스는 EUR 사용
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

# 입력 금액을 원(KRW)으로 변환 (프랑스에서는 EUR → KRW 변환 적용)
def convert_to_krw(amount, from_currency):
    try:
        # 만약 이미 KRW이면 변환 없이 그대로 반환
        if from_currency == "KRW":
            return int(amount)  # 정수로 변환하여 그대로 반환

        # 프랑스인 경우 EUR → KRW 변환 수행, 다른 경우 USD → KRW 변환
        base_currency = "EUR" if from_currency == "EUR" else "USD"

        # 기준 환율 가져오기 (exchangerate.host 사용)
        res = requests.get(f"https://api.exchangerate.host/latest?base={base_currency}")
        data = res.json()

        print("[API 응답 확인]", data)  # 디버깅용 출력

        if "rates" not in data or "KRW" not in data["rates"]:
            print("[CONVERT ERROR] API 응답 없음, 기본 환율 적용")
            return round(amount * (1470 if from_currency == "EUR" else 1300))  # 기본 환율 적용

        currency_to_krw = data["rates"]["KRW"]
        return round(amount * currency_to_krw)  # 정수 반올림
    except Exception as e:
        print("[CONVERT ERROR]", e)
        return round(amount * (1470 if from_currency == "EUR" else 1300))  # 예외 발생 시 기본 환율 적용

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

            # 숫자 검증: 소수점 포함 허용 + 음수 검사
            try:
                input_price = float(input_price)  # 숫자로 변환 시도
                if input_price <= 0:  # 음수 또는 0 입력 시 오류 메시지 출력
                    error_message = "금액은 0보다 커야 합니다."
                else:
                    converted_price = convert_to_krw(input_price, currency_code)
            except ValueError:
                error_message = "유효한 숫자를 입력하세요."  # 변환 실패 시 오류 메시지
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
