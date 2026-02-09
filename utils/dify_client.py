"""
Dify工作流客户端封装
用于调用Dify工作流API进行新闻审核
"""
import asyncio
import json
from typing import Dict, Any, Optional
import aiohttp
from utils.logger import logger


class DifyClient:
    """Dify工作流API客户端"""
    
    def __init__(self):
        """初始化Dify客户端"""
        self.api_key = "app-11UCJJckzZQIu14r1TZrllQm"
        self.endpoint = "http://kno.fridgechannels.com/v1/workflows/run"
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
    
    async def run_workflow(self, play_raw_news_id: int) -> Dict[str, Any]:
        """
        调用Dify工作流接口
        
        Args:
            play_raw_news_id: play_raw_news表的记录ID
            
        Returns:
            包含status字段的响应字典，格式如: {"status": "APPROVE", ...}
            如果调用失败，返回 {"error": "错误信息"}
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {
                "play_raw_news_id": play_raw_news_id
            },
            "response_mode": "blocking",
            "user": "abc-123"
        }
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # 详细日志：打印完整的响应结构（用于诊断字段位置问题）
                        logger.info(
                            f"Dify工作流调用成功: play_raw_news_id={play_raw_news_id}\n"
                            f"完整响应JSON:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                        )
                        return result
                    else:
                        error_text = await response.text()
                        error_msg = f"HTTP {response.status}: {error_text}"
                        logger.error(f"Dify工作流调用失败: play_raw_news_id={play_raw_news_id}, {error_msg}")
                        return {"error": error_msg}
        
        except asyncio.TimeoutError:
            error_msg = "请求超时"
            logger.error(f"Dify工作流调用超时: play_raw_news_id={play_raw_news_id}")
            return {"error": error_msg}
        
        except aiohttp.ClientError as e:
            error_msg = f"网络错误: {str(e)}"
            logger.error(f"Dify工作流调用网络错误: play_raw_news_id={play_raw_news_id}, {error_msg}")
            return {"error": error_msg}
        
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"Dify工作流调用失败: play_raw_news_id={play_raw_news_id}, {error_msg}", exc_info=True)
            return {"error": error_msg}
    
    def is_approved(self, response: Dict[str, Any]) -> bool:
        """
        检查响应中的 data.outputs.status 是否为 APPROVE（通过）
        
        Args:
            response: Dify API返回的响应字典
            
        Returns:
            如果 data.outputs.status 为 "APPROVE" 返回 True，否则返回 False
        """
        if "error" in response:
            logger.debug("is_approved检查: 响应包含error字段，返回False")
            return False
        
        data = response.get("data")
        if not isinstance(data, dict):
            return False
        
        outputs = data.get("outputs")
        if not isinstance(outputs, dict):
            return False
        
        status = outputs.get("status")
        is_approved_result = isinstance(status, str) and status.upper() == "APPROVE"
        logger.debug(f"is_approved检查: data.outputs.status='{status}' -> {is_approved_result}")
        return is_approved_result


# 全局Dify客户端实例
dify_client = DifyClient()
