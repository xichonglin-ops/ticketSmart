"""
12306抢票软件配置文件
"""

# 12306 API URLs
URLS = {
    # 登录相关
    "login_init": "https://kyfw.12306.cn/otn/login/init",
    "login_check": "https://kyfw.12306.cn/passport/web/login",
    "uamtk": "https://kyfw.12306.cn/passport/web/auth/uamtk",
    "uamauthclient": "https://kyfw.12306.cn/otn/uamauthclient",
    "get_captcha": "https://kyfw.12306.cn/passport/captcha/captcha-image64",
    "check_captcha": "https://kyfw.12306.cn/passport/captcha/captcha-check",

    # 用户信息
    "get_passengers": "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs",
    "user_info": "https://kyfw.12306.cn/otn/modifyUser/initQueryUserInfoApi",

    # 查询相关
    "query_ticket": "https://kyfw.12306.cn/otn/leftTicket/queryE",
    "query_ticket_price": "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice",
    "station_name": "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js",

    # 订票相关
    "submit_order": "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest",
    "init_dc": "https://kyfw.12306.cn/otn/confirmPassenger/initDc",
    "check_order_info": "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo",
    "get_queue_count": "https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount",
    "confirm_single": "https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue",
    "query_order_wait": "https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime",
    "result_order": "https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue",

    # 订单查询
    "query_no_complete": "https://kyfw.12306.cn/otn/queryOrder/queryMyOrderNoComplete",
}

# 请求头 - 模拟Chrome浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# 座位类型代码
SEAT_TYPES = {
    "商务座": "9",
    "一等座": "M",
    "二等座": "O",
    "高级软卧": "6",
    "软卧": "4",
    "动卧": "F",
    "硬卧": "3",
    "软座": "2",
    "硬座": "1",
    "无座": "1",  # 无座和硬座代码相同
}

# 座位类型名称（用于显示）
SEAT_TYPE_NAMES = {
    "9": "商务座",
    "M": "一等座",
    "O": "二等座",
    "6": "高级软卧",
    "4": "软卧",
    "F": "动卧",
    "3": "硬卧",
    "2": "软座",
    "1": "硬座",
    "WZ": "无座",
}

# 乘客类型
PASSENGER_TYPES = {
    "成人": "1",
    "儿童": "2",
    "学生": "3",
    "残军": "4",
}

# 证件类型
ID_TYPES = {
    "二代身份证": "1",
    "港澳通行证": "C",
    "台湾通行证": "G",
    "护照": "B",
}

# 抢票配置
TICKET_CONFIG = {
    "query_interval": 1.5,  # 查询间隔（秒），适当增加避免限流
    "max_retry": 100,  # 最大重试次数
    "submit_retry": 5,  # 提交订单重试次数
}
