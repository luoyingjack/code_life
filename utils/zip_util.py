import zipfile
from itertools import product

# 密码字符范围
chars = """
qwertyuiopasdfghjklzxcvbnm1234567890QWERTYUIOPASDFGHJKLZXCVBNM
"""

length = 1  # 密码长度，从第n位开始破解，如果第n位没有，则从n+1位开始，以此类推
file_name = '哈哈.rtf.zip'
def bruteForce(zip_file):
    try:
        myZip = zipfile.ZipFile(zip_file)
    except FileExistsError:
        print('传入文件不存在')
        return

    global length
    while True:
        passwords = product(chars, repeat=length)
        i = 1
        for password in passwords:
            password = ''.join(password)
            try:
                myZip.extractall(pwd=password.encode())
                print(f'第{i}次解析，恭喜你，密码正确: {password}')
                return
            except Exception:
                if i % 10000 == 0:
                    print(f'第{i}次，解析中...')
                i += 1
        length += 1

bruteForce(file_name)