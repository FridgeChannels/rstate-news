"""
测试脚本：直接调用 Dify API 并输出完整响应结构
用于诊断 is_approved() 判断逻辑问题
"""
import asyncio
import json
from utils.dify_client import dify_client
from utils.logger import logger


async def test_dify_response():
    """测试 Dify API 响应结构"""
    # 使用一个已知存在的 play_raw_news_id（从数据库获取一个最近的ID）
    # 如果不知道，可以先用一个测试ID，或者从数据库查询
    test_id = 1  # 你可以改成数据库里实际存在的ID
    
    logger.info("=" * 60)
    logger.info("开始测试 Dify API 响应结构")
    logger.info("=" * 60)
    logger.info(f"测试 play_raw_news_id: {test_id}")
    logger.info("")
    
    try:
        # 调用 Dify API
        response = await dify_client.run_workflow(test_id)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("响应接收完成，开始 is_approved() 检查")
        logger.info("=" * 60)
        
        # 检查是否通过
        is_approved = dify_client.is_approved(response)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"最终判断结果: is_approved = {is_approved}")
        logger.info("=" * 60)
        
        # 额外输出：手动检查所有可能的字段路径
        logger.info("")
        logger.info("手动检查所有可能的字段路径:")
        logger.info(f"  response.keys() = {list(response.keys())}")
        if "data" in response:
            logger.info(f"  response['data'].keys() = {list(response.get('data', {}).keys())}")
            if "outputs" in response.get("data", {}):
                logger.info(f"  response['data']['outputs'].keys() = {list(response.get('data', {}).get('outputs', {}).keys())}")
        if "outputs" in response:
            logger.info(f"  response['outputs'].keys() = {list(response.get('outputs', {}).keys())}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_dify_response())
