# -*- coding: utf-8 -*-
"""
双色球 AI 预测自动生成脚本
自动调用 AI 模型生成下期预测数据
"""

import json
import os
import sys
from datetime import datetime, timedelta

import requests
from openai import OpenAI
from typing import Dict, Any
import fetch_history
from fetch_history import fetch_lottery_history
from four_pillars import calculate_four_pillars, calculate_personal_bazi

# ==================== 配置区 ====================
# API 配置（通过环境变量设置）
BASE_URL = os.environ.get("SSQ_AI_BASE_URL")
API_KEY = os.environ.get("SSQ_AI_API_KEY","1")
PUSH_PLUS_TOKEN = os.environ.get("SSQ_PUSH_PLUS_TOKEN")

#微信
PUSH_WX_URL = os.environ.get("SSQ_PUSH_WX_URL","http://ray.1314921.xyz:8800/notify/send/message")
PUSH_WX_USER = os.environ.get("SSQ_PUSH_WX_USER","QinFengRui")
PUSH_WX_TOKEN = os.environ.get("SSQ_PUSH_WX_TOKEN","50944378")

ba_zi =  os.environ.get("SSQ_BA_ZI")
if not API_KEY:
    print("❌ 请设置环境变量 AI_API_KEY")
    sys.exit(1)

# 模型配置列表
MODELS = [
    {"id": "glm-5.1", "name": "glm-5.1", "model_id": "glm-5.1"},
    {"id": "gemini-3-flash-preview", "name": "gemini-3-flash-preview", "model_id": "gemini-3-flash-preview"},
    {"id": "sensenova-6.7-flash-lite", "name": "sensenova-6.7-flash-lite", "model_id": "sensenova-6.7-flash-lite"},
    {"id": "deepseek-v4-flash", "name": "deepseek-v4-flash", "model_id": "deepseek-v4-flash"}
]

# 文件路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOTTERY_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "lottery_history.json")
AI_PREDICTIONS_FILE = os.path.join(SCRIPT_DIR, "data", "ai_predictions.json")
PREDICTIONS_HISTORY_FILE = os.path.join(SCRIPT_DIR, "data", "predictions_history.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "doc", "prompt3.0.md")
CHOICE_FILE = os.path.join(SCRIPT_DIR, "doc", "prompt3.1.md")

# ==================== 工具函数 ====================

def load_prompt_template(file: str) -> str:
    """加载 Prompt 模板文件"""
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ 加载 Prompt 文件失败: {str(e)}")
        raise

def load_lottery_history() -> Dict[str, Any]:
    """加载历史开奖数据"""
    try:
        with open(LOTTERY_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载历史数据失败: {str(e)}")
        raise

def get_next_draw_date() -> str:
    """
    根据双色球开奖规则（每周二、四、日 21:15）计算下期开奖日期
    返回 YYYY-MM-DD 格式
    """
    today = datetime.now()
    weekday = today.weekday()  # 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日

    # 开奖日: 周二(1), 周四(3), 周日(6)
    draw_weekdays = [1, 3, 6]

    # 如果今天是开奖日且未到开奖时间(21:15)，则预测今天
    if weekday in draw_weekdays:
        draw_time = today.replace(hour=21, minute=15, second=0, microsecond=0)
        if today < draw_time:
            return today.strftime("%Y-%m-%d")

    # 否则找下一个开奖日
    for days_ahead in range(1, 8):
        future_date = today + timedelta(days=days_ahead)
        if future_date.weekday() in draw_weekdays:
            return future_date.strftime("%Y-%m-%d")

    # 理论上不会到这里
    return today.strftime("%Y-%m-%d")

def get_openai_client() -> OpenAI:
    """获取 OpenAI 客户端"""
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)

def extract_json_from_response(response_text: str) -> str:
    """从 AI 响应中提取 JSON 内容"""
    # 去除可能的 markdown 标记
    text = response_text.strip()

    # 如果有 ```json 标记，提取中间的内容
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    return text

def call_ai_model(client: OpenAI, model_config: Dict[str, str], prompt: str) -> Dict[str, Any]:
    """调用 AI 模型获取预测"""
    try:
        print(f"  ⏳ 正在调用 {model_config['name']} 模型...")

        response = client.chat.completions.create(
            model=model_config['id'],
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的彩票数据分析师，擅长基于历史数据进行模式分析和预测。请严格按照要求返回 JSON 格式数据，不要有任何额外的解释或说明。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )

        response_text = response.choices[0].message.content.strip()

        # 提取 JSON
        json_text = extract_json_from_response(response_text)

        # 解析 JSON
        prediction_data = json.loads(json_text)

        print(f"  ✅ {model_config['name']} 预测成功")
        return prediction_data

    except json.JSONDecodeError as e:
        print(f"  ❌ {model_config['name']} JSON 解析失败: {str(e)}")
        print(f"  原始响应前500字符:\n{response_text[:500]}")
        raise
    except Exception as e:
        print(f"  ❌ {model_config['name']} 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        import traceback
        print(f"  详细堆栈:\n{traceback.format_exc()}")
        raise

def validate_prediction(prediction: Dict[str, Any]) -> bool:
    """验证预测数据格式"""
    try:
        # 检查必需字段
        required_fields = ["prediction_date", "target_period", "model_id", "model_name", "predictions"]
        for field in required_fields:
            if field not in prediction:
                print(f"    ⚠️  缺少字段: {field}")
                return False

        # 检查预测组数量
        if len(prediction["predictions"]) != 6:
            print(f"    ⚠️  预测组数量不正确: {len(prediction['predictions'])}")
            return False

        # 检查每组预测
        for group in prediction["predictions"]:
            # 检查红球
            if len(group["red_balls"]) != 6:
                print(f"    ⚠️  红球数量不正确: {len(group['red_balls'])}")
                return False

            # 检查红球是否排序
            sorted_reds = sorted(group["red_balls"])
            if group["red_balls"] != sorted_reds:
                print(f"    ⚠️  红球未排序: {group['red_balls']}")
                return False

            # 检查蓝球
            if not group["blue_ball"]:
                print(f"    ⚠️  蓝球为空")
                return False

        return True

    except Exception as e:
        print(f"    ⚠️  验证出错: {str(e)}")
        return False

def generate_predictions() -> Dict[str, Any]:
    """生成所有模型的预测"""
    print("\n" + "="*50)
    print("🤖 双色球 AI 预测自动生成")
    print("="*50 + "\n")

    # 加载 Prompt 模板
    print("📄 加载 Prompt 模板...")
    try:
        prompt_template = load_prompt_template(PROMPT_FILE)
        print(f"  ✓ Prompt 模板加载成功 ({len(prompt_template)} 字符)\n")
    except Exception as e:
        print(f"  ✗ Prompt 模板加载失败: {str(e)}\n")
        return None

    # 加载历史数据
    print("📊 加载历史开奖数据...")
    lottery_data = load_lottery_history()

    # 归档旧预测（如果已开奖）
    archive_old_prediction(lottery_data)

    # 获取下期信息
    next_draw = lottery_data.get("next_draw", {})
    target_period = next_draw.get("next_period", "")
    target_date = next_draw.get("next_date_display", "")

    if not target_period:
        print("❌ 无法获取下期期号信息")
        return None

    print(f"🎯 目标期号: {target_period}")
    print(f"📅 开奖日期: {target_date}")
    print(f"📝 历史数据: 最近 {len(lottery_data.get('data', []))} 期\n")

    # 准备历史数据（最近30期）
    history_data = lottery_data.get("data", [])[:30]
    history_json = json.dumps(history_data, ensure_ascii=False, indent=2)

    # 预测日期：根据开奖规则计算下期开奖日期
    prediction_date = get_next_draw_date()
    print(f"📅 预测日期: {prediction_date}\n")

    # 初始化 OpenAI 客户端
    client = get_openai_client()

    # 存储所有模型的预测
    all_predictions = []

    # 逐个调用模型
    print("🔮 开始生成预测...\n")
    for model_config in MODELS:
        try:
            # 构建 prompt
            prompt = prompt_template.format(
                target_period=target_period,
                target_date=target_date,
                lottery_history=history_json,
                prediction_date=prediction_date,
                model_id=model_config['model_id'],
                model_name=model_config['name']
            )

            # 调用模型
            prediction = call_ai_model(client, model_config, prompt)

            # 验证数据
            if validate_prediction(prediction):
                all_predictions.append(prediction)
                print(f"  ✓ 验证通过\n")
            else:
                print(f"  ✗ 验证失败，跳过该模型\n")

        except Exception as e:
            print(f"  ✗ 处理 {model_config['name']} 时失败")
            print(f"  错误类型: {type(e).__name__}")
            print(f"  错误信息: {str(e)}\n")
            continue

    # 构建最终输出
    if not all_predictions:
        print("❌ 没有成功生成任何预测")
        return None

    result = {
        "prediction_date": prediction_date,
        "target_period": target_period,
        "target_date": target_date,
        "models": all_predictions
    }

    print(f"✅ 成功生成 {len(all_predictions)}/{len(MODELS)} 个模型的预测\n")
    return result

def calculate_hit_result(prediction_group: Dict[str, Any], actual_result: Dict[str, Any]) -> Dict[str, Any]:
    """计算单组预测的命中结果"""
    red_hits = [b for b in prediction_group["red_balls"] if b in actual_result["red_balls"]]
    blue_hit = prediction_group["blue_ball"] == actual_result["blue_ball"]

    return {
        "red_hits": red_hits,
        "red_hit_count": len(red_hits),
        "blue_hit": blue_hit,
        "total_hits": len(red_hits) + (1 if blue_hit else 0)
    }

def archive_old_prediction(lottery_data: Dict[str, Any]):
    """将旧预测归档到历史记录（如果已开奖）"""
    try:
        # 检查是否存在旧预测文件
        if not os.path.exists(AI_PREDICTIONS_FILE):
            print("  ℹ️  没有旧预测需要归档\n")
            return

        # 读取旧预测
        with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            old_predictions = json.load(f)

        old_target_period = old_predictions.get("target_period")
        if not old_target_period:
            print("  ⚠️  旧预测文件格式异常，跳过归档\n")
            return

        # 检查该期号是否已开奖
        latest_period = lottery_data.get("data", [{}])[0].get("period")
        if not latest_period or int(old_target_period) > int(latest_period):
            print(f"  ℹ️  旧预测期号 {old_target_period} 尚未开奖，无需归档\n")
            return

        print(f"  📦 旧预测期号 {old_target_period} 已开奖，开始归档...")

        # 查找实际开奖结果
        actual_result = None
        for draw in lottery_data.get("data", []):
            if draw.get("period") == old_target_period:
                actual_result = draw
                break

        if not actual_result:
            print(f"  ⚠️  找不到期号 {old_target_period} 的开奖结果，跳过归档\n")
            return

        # 读取历史记录文件
        history_data = {"predictions_history": []}
        if os.path.exists(PREDICTIONS_HISTORY_FILE):
            with open(PREDICTIONS_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

        # 检查该期号是否已存在
        existing_record = next((r for r in history_data["predictions_history"]
                               if r["target_period"] == old_target_period), None)

        if existing_record:
            print(f"  ℹ️  期号 {old_target_period} 已存在于历史记录中\n")
            return

        # 为每个模型计算命中结果
        models_with_hits = []
        for model_data in old_predictions.get("models", []):
            # 为每组预测计算命中
            predictions_with_hits = []
            for pred_group in model_data.get("predictions", []):
                pred_with_hit = pred_group.copy()
                pred_with_hit["hit_result"] = calculate_hit_result(pred_group, actual_result)
                predictions_with_hits.append(pred_with_hit)

            # 找出最佳预测组
            best_pred = max(predictions_with_hits, key=lambda p: p["hit_result"]["total_hits"])

            models_with_hits.append({
                "model_id": model_data.get("model_id"),
                "model_name": model_data.get("model_name"),
                "predictions": predictions_with_hits,
                "best_group": best_pred["group_id"],
                "best_hit_count": best_pred["hit_result"]["total_hits"]
            })

        # 创建新的历史记录
        new_record = {
            "prediction_date": old_predictions.get("prediction_date"),
            "target_period": old_target_period,
            "actual_result": actual_result,
            "models": models_with_hits
        }

        # 插入到历史记录顶部
        history_data["predictions_history"].insert(0, new_record)

        # 保存历史记录
        with open(PREDICTIONS_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ 已将期号 {old_target_period} 的预测归档到历史记录")
        print(f"  📊 归档模型数: {len(models_with_hits)}\n")

    except Exception as e:
        print(f"  ⚠️  归档旧预测时出错: {str(e)}")
        print(f"  继续生成新预测...\n")

def save_predictions(predictions: Dict[str, Any]):
    """保存预测数据到文件"""
    try:
        print("💾 保存预测数据...")

        # 创建备份
        if os.path.exists(AI_PREDICTIONS_FILE):
            backup_file = AI_PREDICTIONS_FILE.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已创建备份: {os.path.basename(backup_file)}")

        # 保存新预测
        with open(AI_PREDICTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)

        print(f"  ✓ 已保存到: {AI_PREDICTIONS_FILE}\n")

    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")
        raise

def load_ai_predictions() -> Dict[str, Any]:
    """加载历史开奖数据"""
    try:
        with open(AI_PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载历史数据失败: {str(e)}")
        raise

def _parse_bazi_hour(bazi_hour) -> int:
    """
    将各种格式的时间转换为小时整数（0-23）

    支持格式：
      - int:              21           → 21
      - "HH:MM":         "21:15"      → 21
      - "HH:MM-HH:MM":   "21:00-23:00"→ 21（取起始小时）
      - "HH:MM~HH:MM":   "21:00~23:00"→ 21（取起始小时）
    """
    if isinstance(bazi_hour, int):
        return bazi_hour
    s = str(bazi_hour).strip()
    # 取范围起始部分（支持 - 和 ~ 分隔）
    for sep in ['-', '~']:
        if sep in s:
            s = s.split(sep)[0].strip()
            break
    # 解析 HH:MM 或 HH
    if ':' in s:
        return int(s.split(':')[0])
    return int(s)


def choice_predictions_data(target_period, target_date, prediction_date,
                             bazi_date, bazi_hour,
                             birth_place,
                             live_place,
                            shi_chen='巳'):
    """
    生成评估预测数据

    :param target_period:   目标期号，如 '26075'
    :param target_date:     开奖日期显示字符串，如 '2026年07月02日'（不做修改，仅用于展示）
    :param prediction_date: 预测日期，ISO格式 'YYYY-MM-DD'
    :param bazi_date:       用于计算开奖日四柱的公历日期，ISO格式 'YYYY-MM-DD'
    :param bazi_hour:       开奖时刻，支持多种格式（默认 '21:15'，即亥时）：
                              - int 整数：21
                              - 时间字符串：'21:15'
                              - 时间范围字符串：'21:00-23:00' 或 '21:00~23:00'（取起始小时）
    :param shi_chen:        命主出生时辰（如 '巳'）
    :param birth_place:     命主出生地（如 '河南信阳'）
    :param live_place:      命主居住地（如 '广东深圳'）
    """
    dt = datetime.strptime(bazi_date, "%Y-%m-%d")
    lunar_year = int(dt.year)
    lunar_month = int(dt.month)
    lunar_day = int(dt.day)
    # 解析开奖时刻为小时整数
    hour = _parse_bazi_hour(bazi_hour)

    # 加载 Prompt 模板
    print("📄 加载 评估 Prompt 模板...")
    try:
        prompt_template = load_prompt_template(CHOICE_FILE)
        print(f"  ✓ ai Prompt 评估模板加载成功 ({len(prompt_template)} 字符)\n")
    except Exception as e:
        print(f"  ✗ Prompt 评估模板加载失败: {str(e)}\n")
        return None

    # 加载历史数据
    print("📊 加载AI生成数据...")
    ai_data = load_ai_predictions()
    ai_predictions = json.dumps(ai_data, ensure_ascii=False, indent=2)

    # 计算开奖日四柱八字
    # bazi_date: 公历ISO格式 "YYYY-MM-DD"
    # bazi_hour: 原始传入值（如 "21:00-23:00"），解析为 hour 整数后传给 calculate_four_pillars
    print(f"🔯 计算开奖日四柱八字（{bazi_date} {bazi_hour}，解析时刻 hour={hour}）...")
    four_pillars_data = calculate_four_pillars(bazi_date, hour=hour)
    four_pillars_json = json.dumps(four_pillars_data, ensure_ascii=False, indent=2)

    # 动态计算命主八字（根据传入参数）
    if lunar_year and lunar_month and lunar_day:
        personal_bazi = calculate_personal_bazi(
            lunar_year=lunar_year,
            lunar_month=lunar_month,
            lunar_day=lunar_day,
            shi_chen=shi_chen,
            birth_place=birth_place,
            live_place=live_place
        )
    else:
        print("no")

    personal_bazi_json = json.dumps(personal_bazi, ensure_ascii=False, indent=2)
    print(f"  ✓ 开奖日四柱：{four_pillars_data.get('four_pillars_gz', '')}")
    print(f"  ✓ 命主八字：{personal_bazi.get('four_pillars_str', '')}\n")

    # 初始化 OpenAI 客户端
    client = get_openai_client()

    # 存储所有模型的预测
    all_predictions = []

    # 逐个调用模型
    print("🔮 开始生成预测...\n")
    for model_config in MODELS:
        if model_config['id'] != 'glm-5.1':
            print("非glm-5.2，跳过预测")
            continue
        try:
            # 构建 prompt
            prompt = prompt_template.format(
                target_period=target_period,
                target_date=target_date,
                ai_predictions=ai_predictions,
                prediction_date=prediction_date,
                model_id=model_config['model_id'],
                model_name=model_config['name'],
                four_pillars=four_pillars_json,
                personal_bazi=personal_bazi_json,
            )

            # 调用模型
            prediction = call_ai_data_model(client, model_config, prompt)
            print(prediction)
            try:
                if PUSH_PLUS_TOKEN is not None:
                    send_push_plus("双色球预测结果", prediction, PUSH_PLUS_TOKEN)
            except Exception as e:
                print(f"send_push_plus错误信息: {str(e)}\n")
            try:
                if PUSH_WX_TOKEN is not None:
                    send_push_wx(prediction)
            except Exception as e:
                print(f"send_push_wx错误信息: {str(e)}\n")
        except Exception as e:
            print(f"  ✗ 处理 {model_config['name']} 时失败")
            print(f"  错误类型: {type(e).__name__}")
            print(f"  错误信息: {str(e)}\n")
            continue

def call_ai_data_model(client: OpenAI, model_config: Dict[str, str], prompt: str) -> Dict[str, Any]:
    """调用 AI 模型获取预测"""
    try:
        print(f"  ⏳ 正在调用 {model_config['name']} 模型...")

        response = client.chat.completions.create(
            model=model_config['id'],
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的彩票数据分析师，擅长基于历史数据进行模式分析和预测。请严格按照要求返回markdown格式数据，不要有任何额外的解释或说明。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8
        )

        response_text = response.choices[0].message.content.strip()

        print(f"  ✅ {model_config['name']} 预测成功")
        return response_text

    except json.JSONDecodeError as e:
        print(f"  ❌ {model_config['name']} JSON 解析失败: {str(e)}")
        print(f"  原始响应前500字符:\n{response_text[:500]}")
        raise
    except Exception as e:
        print(f"  ❌ {model_config['name']} 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        import traceback
        print(f"  详细堆栈:\n{traceback.format_exc()}")
        raise

def main():
    """主函数"""
    try:

        fetch_lottery_history.main()
        # 生成预测
        predictions = generate_predictions()

        if predictions:
            # 保存预测
            save_predictions(predictions)

            print("="*50)
            print("🎉 预测生成完成！")
            print("="*50 + "\n")

            # 显示预测摘要
            print("📋 预测摘要:")
            print(f"  期号: {predictions['target_period']}")
            print(f"  日期: {predictions['prediction_date']}")
            print(f"  模型数量: {len(predictions['models'])}")
            for model in predictions['models']:
                print(f"    - {model['model_name']}")
            print()
        else:
            print("❌ 预测生成失败")

        # bazi_date: 开奖日公历日期（ISO格式）
        # bazi_hour: 开奖时刻，支持 int/时间字符串/时间范围字符串
        #   双色球固定 21:15 开奖（亥时 21:00-23:00），可传入以下任意格式：
        #     bazi_hour=21             → 整数
        #     bazi_hour='21:15'        → 精确时刻
        #     bazi_hour='21:00-23:00'  → 时间范围（取起始小时）
        province_city1=""   # 出生地
        province_city2=""  #居住地
        date_part=""  # 1996-12-13
        time_part="" # 9:00-10
        if ba_zi:
            # 1. 首先用 '&' 将四大块内容切开
            parts = ba_zi.split('&')

            # 2. 分别赋值给对应的变量
            province_city1 = parts[0]
            province_city2 = parts[1]
            date_part = parts[2]  # 1992-12-13
            time_part = parts[3]  # 9:00-10
        choice_predictions_data(predictions['target_period'],predictions['target_date'], predictions['prediction_date'],
                                date_part,
                                time_part,
                                province_city1,
                                province_city2)
        # choice_predictions_data("1992-12-13", '1992-12-13',
        #                         "2026-07-05",
        #                         date_part,
        #                         time_part,
        #                         province_city1,
        #                         province_city2)

    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        raise


def send_push_plus(title, content, token):
    """
    使用 pushplus 发送 HTML 模板通知
    """
    # 基础 URL
    base_url = "https://www.pushplus.plus/send"
    # 构建请求参数
    # 使用 params 参数，requests 库会自动帮你进行 URL 编码（解决中文乱码问题）
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown"
    }
    try:
        # 发送 GET 请求
        response = requests.get(base_url, json=payload)
        # 解析返回的 JSON 结果
        result = response.json()
        # 状态码 200 通常代表 pushplus 接口响应成功
        if result.get("code") == 200:
            print(f"【推送成功】: {result.get('msg')}")
        else:
            print(f"【推送失败】: 错误码 {result.get('code')}, 原因: {result.get('msg')}")
        return result
    except Exception as e:
        print(f"【pushplus请求发生异常】: {e}")
        return None

def send_push_wx(content):
    """
    使用 pushplus 发送 HTML 模板通知
    """
    # 基础 URL
    base_url = PUSH_WX_URL
    # 构建请求参数
    # 使用 params 参数，requests 库会自动帮你进行 URL 编码（解决中文乱码问题）
    payload = {
        "token": PUSH_WX_TOKEN,
        "touser": PUSH_WX_USER,
        "content": content
    }
    try:
        # 发送 GET 请求
        response = requests.post(base_url, json=payload)
        # 解析返回的 JSON 结果
        result = response.json()
        # 状态码 200 通常代表 pushplus 接口响应成功
        if result.get("errcode") == 0:
            print(f"【推送成功 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】: {result.get('errmsg')}")
        else:
            print(f"【推送失败】: 错误码 {result.get('errcode')}, 原因: {result.get('errmsg')}")
        return result
    except Exception as e:
        print(f"【PUSH_WX请求发生异常】: {e}")
        return None

if __name__ == "__main__":
    main()