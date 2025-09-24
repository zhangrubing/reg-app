#!/usr/bin/env python3
"""简单API测试脚本"""
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8083"

def test_basic_apis():
    """测试基本API"""
    print("🚀 开始测试基本API...")
    
    # 测试登录
    print("\n📋 测试登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/login", json=login_data)
    print(f"登录状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"登录成功: {data}")
        token = response.cookies.get('auth')
        print(f"获取token: {token[:20] if token else 'None'}")
    else:
        print(f"登录失败: {response.text}")
        return
    
    # 测试设备列表（使用cookie）
    print("\n📋 测试设备列表...")
    cookies = {'auth': token} if token else {}
    response = requests.get(f"{BASE_URL}/api/devices", cookies=cookies)
    print(f"设备列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"设备数量: {len(data.get('data', []))}")
    else:
        print(f"设备列表失败: {response.text}")
    
    # 测试设备统计
    print("\n📋 测试设备统计...")
    response = requests.get(f"{BASE_URL}/api/devices/stats", cookies=cookies)
    print(f"设备统计状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"设备统计: {data.get('data', {})}")
    else:
        print(f"设备统计失败: {response.text}")
    
    # 测试用户列表
    print("\n📋 测试用户列表...")
    response = requests.get(f"{BASE_URL}/users", cookies=cookies)
    print(f"用户列表状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"用户数量: {data.get('total', 0)}")
    else:
        print(f"用户列表失败: {response.text}")
    
    # 测试用户统计
    print("\n📋 测试用户统计...")
    response = requests.get(f"{BASE_URL}/users/statistics", cookies=cookies)
    print(f"用户统计状态: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"用户统计: {data}")
    else:
        print(f"用户统计失败: {response.text}")

if __name__ == "__main__":
    test_basic_apis()
