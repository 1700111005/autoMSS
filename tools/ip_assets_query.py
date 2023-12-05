# 导入pymysql模块
try:
    import pymysql
except ImportError:
    print("导入pymysql模块失败，请检查是否已经安装")

# 连接数据库
def ip_assests(ip:str)->str:
    try:
        conn = pymysql.connect(host='rm-cn-5yd3fj0ei0004tko.rwlb.rds.aliyuncs.com', port=3306, user='testuser',
                               password='Testuser@321', db='agent')
    except pymysql.Error as e:
        print("连接数据库失败，错误信息为：", e)

    # 获取游标
    cursor = conn.cursor()

    # 查询IP地址为172.24.158.39的资产信息
    sql = "SELECT * FROM assets WHERE ipaddress = %s"
    cursor.execute(sql, (ip,))
    xinxi = ""
    # 获取查询结果
    if cursor.rowcount == 0:
        print("没有找到符合条件的资产信息")
    else:
        result = cursor.fetchall()
        # 打印查询结果
        for row in result:
            item = {
                "资产ID": row[0],
                "索引": row[1],
                "IP地址": row[2],
                "主机名": row[3],
                "操作系统": row[4],
                "中间件": row[5],
                "数据库": row[6],
                "域名": row[7],
                "管理者": row[8],
                "操作员姓名": row[9],
                "电话": row[10]
            }
            xinxi+=str(item)
        # 关闭游标和连接
    cursor.close()
    conn.close()
    return xinxi
if __name__ == '__main__':
    print(ip_assests("111.32.177.97 37975"))