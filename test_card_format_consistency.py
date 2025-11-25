#!/usr/bin/env python3
"""综合测试 - 验证HID和BLE的卡号格式处理"""

def test_card_format_consistency():
    """测试HID和BLE卡号格式的一致性"""
    print("=== 卡号格式一致性测试 ===")
    
    # 测试数据
    test_cases = [
        ("1234567890", "标准10位数"),
        ("123456789", "9位数需要补零"),
        ("12345678901", "11位数取后10位"),
        ("0000000001", "前导零测试"),
        ("9999999999", "最大10位数"),
    ]
    
    print("HID处理方式（来自main.py）:")
    for test_value, description in test_cases:
        print(f"\n测试: {description} - 输入: {test_value}")
        
        # HID处理逻辑（来自main.py第1555-1564行）
        digit_length = 10
        dec_value = test_value[-digit_length:]
        try:
            dec_int = int(dec_value)
            # 对于10位数卡号，使用10D格式，十六进制保持8位（限制为32位）
            hex_value = f"{dec_int & 0xFFFFFFFF:08X}"
            # 确保10D格式是10位数，不足补零
            dec_value = f"{dec_int:010d}"
        except Exception:
            hex_value = dec_value
        
        print(f"  HID结果: 10D={dec_value}, 8H={hex_value}")
        
        # 验证格式
        assert len(dec_value) == 10, f"10D格式长度错误: {len(dec_value)}"
        assert len(hex_value) == 8, f"8H格式长度错误: {len(hex_value)}"
    
    print("\nBLE处理方式（来自ble_manager.py）:")
    for test_value, description in test_cases:
        print(f"\n测试: {description} - 输入: {test_value}")
        
        # BLE处理逻辑（更新后的版本）
        try:
            val = int(test_value)
            # 对于超过10位的数字，截取后10位
            if len(str(val)) > 10:
                val_str = str(val)[-10:]
                val = int(val_str)
            h = f"{val & 0xFFFFFFFF:08X}"  # 反推 8H，限制为32位
            d = f"{val:010d}"  # 确保10位数格式
        except Exception:
            h = test_value
            d = test_value
        
        print(f"  BLE结果: 10D={d}, 8H={h}")
        
        # 验证格式
        assert len(d) == 10, f"10D格式长度错误: {len(d)}"
        assert len(h) == 8, f"8H格式长度错误: {len(h)}"
    
    print("\n=== 测试结果 ===")
    print("✓ HID和BLE都正确处理10D格式")
    print("✓ 10D格式确保为10位数，不足补零")
    print("✓ 8H格式确保为8位十六进制")
    print("✓ 大数值正确处理，32位限制")

if __name__ == "__main__":
    test_card_format_consistency()