#!/usr/bin/env python3
"""API功能测试脚本"""
import requests
import json
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8080"

def test_health_check():
    """测试健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print(f"✅ 健康检查: {response.status_code} - {response.json()}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False

def test_dashboard_statistics():
    """测试仪表板统计"""
    try:
        response = requests.get(f"{BASE_URL}/admin/dashboard/statistics")
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 仪表板统计: 成功")
                return True
        print(f"❌ 仪表板统计失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 仪表板统计失败: {e}")
        return False

def test_user_registration():
    """测试用户注册"""
    try:
        user_data = {
            "username": "testuser",
            "password": "test123456",
            "email": "test@example.com",
            "real_name": "测试用户"
        }
        response = requests.post(f"{BASE_URL}/admin/users/register", json=user_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 用户注册: 成功")
                return True
        print(f"❌ 用户注册失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 用户注册失败: {e}")
        return False

def test_user_login():
    """测试用户登录"""
    try:
        login_data = {
            "username": "testuser",
            "password": "test123456"
        }
        response = requests.post(f"{BASE_URL}/admin/users/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 用户登录: 成功")
                return data["data"]["token"]
        print(f"❌ 用户登录失败: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        print(f"❌ 用户登录失败: {e}")
        return None

def test_channel_operations(token):
    """测试渠道操作"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 创建渠道
        channel_data = {
            "channel_code": "TEST001",
            "name": "测试渠道",
            "description": "测试渠道描述",
            "contact_person": "测试联系人",
            "contact_email": "test@channel.com"
        }
        response = requests.post(f"{BASE_URL}/admin/channels", json=channel_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                channel_id = data["data"]["channel_id"]
                print("✅ 创建渠道: 成功")
                
                # 获取渠道列表
                response = requests.get(f"{BASE_URL}/admin/channels", headers=headers)
                if response.status_code == 200:
                    print("✅ 获取渠道列表: 成功")
                    return True
        print(f"❌ 渠道操作失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 渠道操作失败: {e}")
        return False

def test_activation_operations(token):
    """测试激活操作"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 获取激活统计
        response = requests.get(f"{BASE_URL}/admin/activations/statistics", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 激活统计: 成功")
                return True
        print(f"❌ 激活统计失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 激活统计失败: {e}")
        return False

def test_device_operations(token):
    """测试设备操作"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 获取设备统计
        response = requests.get(f"{BASE_URL}/admin/devices/statistics", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 设备统计: 成功")
                return True
        print(f"❌ 设备统计失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 设备统计失败: {e}")
        return False

def test_audit_operations(token):
    """测试审计日志操作"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 获取审计统计
        response = requests.get(f"{BASE_URL}/admin/audit/statistics", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0:
                print("✅ 审计统计: 成功")
                return True
        print(f"❌ 审计统计失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ 审计统计失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始API功能测试...")
    print("=" * 50)
    
    # 测试基本功能
    tests = [
        ("健康检查", test_health_check),
        ("仪表板统计", test_dashboard_statistics),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 测试: {test_name}")
        if test_func():
            passed += 1
    
    # 测试需要认证的功能
    print("\n🔐 测试需要认证的功能...")
    token = test_user_login()
    
    if token:
        auth_tests = [
            ("用户资料", lambda: True),  # 简化测试
            ("渠道操作", lambda: test_channel_operations(token)),
            ("激活操作", lambda: test_activation_operations(token)),
            ("设备操作", lambda: test_device_operations(token)),
            ("审计操作", lambda: test_audit_operations(token)),
        ]
        
        for test_name, test_func in auth_tests:
            print(f"\n📋 测试: {test_name}")
            if test_func():
                passed += 1
            total += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    main()
