"""Unit tests for mobile/prompt_runner.py"""

from mobile.prompt_parser import parse_prompt
from mobile.prompt_runner import build_updated_config


def test_build_updated_config_for_probe_mode():
    base_config = {
        "server_url": "http://127.0.0.1:4723",
        "device_name": "Android",
        "udid": "ABC",
        "platform_version": "16",
        "app_package": "cn.damai",
        "app_activity": ".launcher.splash.SplashMainActivity",
        "item_url": "https://old.example/item",
        "item_id": "123456",
        "keyword": "旧关键词",
        "users": ["张志涛"],
        "city": "北京",
        "date": "04.05",
        "price": "380元",
        "price_index": 0,
        "if_commit_order": True,
        "probe_only": False,
        "auto_navigate": False,
    }
    intent = parse_prompt("帮我抢一张 4 月 6 号张杰的演唱会门票，1280元")
    discovery = {
        "used_keyword": "张杰 演唱会",
        "search_results": [
            {
                "title": "【北京】2026张杰未·LIVE—「开往1982」演唱会-北京站",
                "city": "北京",
                "venue": "国家体育场-鸟巢",
            }
        ],
        "summary": {
            "title": "【北京】2026张杰未·LIVE—「开往1982」演唱会-北京站",
            "venue": "北京市 · 国家体育场-鸟巢",
        },
    }
    selected_price = {"index": 6, "text": "1280元", "tag": "可预约"}

    updated = build_updated_config(base_config, intent, discovery, "04.06", selected_price, "probe")

    assert updated["item_url"] is None
    assert updated["item_id"] is None
    assert updated["keyword"] == "张杰 演唱会"
    assert updated["target_title"] == "【北京】2026张杰未·LIVE—「开往1982」演唱会-北京站"
    assert updated["target_venue"] == "国家体育场-鸟巢"
    assert updated["city"] == "北京"
    assert updated["date"] == "04.06"
    assert updated["price"] == "1280元"
    assert updated["price_index"] == 6
    assert updated["probe_only"] is True
    assert updated["if_commit_order"] is False
    assert updated["auto_navigate"] is True
