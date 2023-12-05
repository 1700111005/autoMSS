import requests

def query_ip_info(target_ip):
    url = f"https://x.threatbook.com/v5/ip/{target_ip}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok" and data.get("data"):
                # 在这里可以根据返回的数据做进一步的判断
                # 如果满足特定条件，可以返回True，否则返回False
                # 例如：如果数据中包含恶意信息，则返回True，否则返回False
                return data.get("data").get("malicious") == 1
            else:
                print("未找到相关情报信息")
                return False
        else:
            print("请求失败，状态码：", response.status_code)
            return False
    except Exception as e:
        print("发生异常：", str(e))
        return False


if __name__ == "__main__":
    target_ip = "47.93.54.234"
    result = query_ip_info(target_ip)
    if result:
        print(f"IP地址 {target_ip} 被判定为恶意")
    else:
        print(f"IP地址 {target_ip} 未被判定为恶意")
