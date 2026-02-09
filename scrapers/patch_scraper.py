"""
Patch.com采集器
采集基于Zipcode的局部新闻
"""
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from scrapers.local_news_scraper import LocalNewsScraper
from scrapers.robust_scraper_mixin import RobustScraperMixin
from utils.logger import logger


class PatchScraper(LocalNewsScraper, RobustScraperMixin):
    """Patch.com新闻采集器"""
    
    def __init__(self, debug_mode: bool = False):
        """
        初始化Patch采集器
        
        Args:
            debug_mode: 是否启用调试模式（headless=False，详细日志，截图）
        """
        super().__init__("Patch")
        self.debug_mode = debug_mode
        # 使用绝对路径，确保目录创建成功
        project_root = Path(__file__).parent.parent
        self.debug_screenshot_dir = project_root / "logs" / "patch_debug_screenshots"
        if self.debug_mode:
            self.debug_screenshot_dir.mkdir(parents=True, exist_ok=True)
            import sys
            print(f"🔍 [DEBUG] 调试模式已启用", flush=True)
            print(f"🔍 [DEBUG] 截图目录: {self.debug_screenshot_dir.absolute()}", flush=True)
            sys.stdout.flush()
    
    async def _take_debug_screenshot(self, page, step_name: str):
        """在调试模式下截图"""
        if self.debug_mode and page:
            try:
                screenshot_path = self.debug_screenshot_dir / f"{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                abs_path = screenshot_path.absolute()
                print(f"🔍 [DEBUG] 截图已保存: {abs_path}")
                logger.info(f"🔍 [DEBUG] 截图已保存: {abs_path}")
            except Exception as e:
                error_msg = f"截图失败: {str(e)}"
                print(f"⚠️ [DEBUG] {error_msg}")
                logger.debug(error_msg)
    
    async def _verify_browser_state(self, page) -> bool:
        """
        验证浏览器、context和page的状态
        
        Args:
            page: Playwright页面对象
            
        Returns:
            True如果浏览器状态有效，False否则
        """
        try:
            # 检查浏览器对象
            if not self.browser:
                logger.warning(f"{self.source_name}: 浏览器对象为None")
                return False
            
            # 检查浏览器连接
            try:
                _ = self.browser.contexts
            except Exception as e:
                logger.warning(f"{self.source_name}: 浏览器连接已断开: {str(e)}")
                return False
            
            # 检查context
            if not self.context:
                logger.warning(f"{self.source_name}: Context对象为None")
                return False
            
            # 检查page
            if not page:
                logger.warning(f"{self.source_name}: Page对象为None")
                return False
            
            # 检查page是否已关闭
            try:
                _ = page.url
            except Exception as e:
                logger.warning(f"{self.source_name}: Page已关闭: {str(e)}")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"{self.source_name}: 浏览器状态检查失败: {str(e)}")
            return False
    
    async def _scrape_zipcode_news(self, zipcode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        采集Patch.com的Zipcode新闻
        
        Args:
            zipcode: 邮政编码
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        articles = []
        page = None
        
        try:
            # 调试模式：使用headless=False以便观察
            import sys
            if self.debug_mode:
                print(f"🔍 [DEBUG] 调试模式已启用，浏览器将以可见模式运行", flush=True)
                print(f"🔍 [DEBUG] 截图将保存到: {self.debug_screenshot_dir}", flush=True)
                sys.stdout.flush()
                logger.info(f"🔍 [DEBUG] 调试模式已启用，浏览器将以可见模式运行")
                logger.info(f"🔍 [DEBUG] 截图将保存到: {self.debug_screenshot_dir}")
            
            print(f"🔍 [DEBUG] 正在启动浏览器...", flush=True)
            sys.stdout.flush()
            # 注意：即使debug_mode=True，也使用headless=True以避免macOS权限问题
            # 调试功能（日志、截图）在headless模式下仍然可用
            # 如果需要观察浏览器窗口，可以手动修改这里为 headless=False
            use_headless = True  # 改为False如果需要观察浏览器窗口
            if self.debug_mode:
                print(f"🔍 [DEBUG] 使用headless={use_headless}模式（调试功能仍然可用）", flush=True)
                sys.stdout.flush()
            await self._setup_browser(headless=use_headless)
            
            if self.debug_mode:
                print(f"🔍 [DEBUG] 浏览器已启动", flush=True)
                sys.stdout.flush()
                logger.info(f"🔍 [DEBUG] 浏览器已启动")
                
                # 立即检查浏览器状态
                if not self.browser:
                    print(f"❌ [DEBUG] 浏览器对象为None！", flush=True)
                    sys.stdout.flush()
                    raise Exception("浏览器启动后对象为None")
                
                # 检查浏览器是否仍然连接
                try:
                    contexts = self.browser.contexts
                    print(f"🔍 [DEBUG] 浏览器连接正常，当前有 {len(contexts)} 个上下文", flush=True)
                    sys.stdout.flush()
                except Exception as e:
                    print(f"❌ [DEBUG] 浏览器连接检查失败: {str(e)}", flush=True)
                    sys.stdout.flush()
                    raise Exception(f"浏览器连接检查失败: {str(e)}")
                
                # 在headless=False模式下，给浏览器更多时间稳定（但分段检查）
                print(f"🔍 [DEBUG] 等待浏览器稳定...", flush=True)
                sys.stdout.flush()
                for i in range(5):  # 5秒，每秒检查一次
                    await asyncio.sleep(1)
                    if not self.browser:
                        print(f"❌ [DEBUG] 浏览器在第 {i+1} 秒时断开！", flush=True)
                        sys.stdout.flush()
                        raise Exception(f"浏览器在等待期间断开（第{i+1}秒）")
                    try:
                        _ = self.browser.contexts
                    except Exception as e:
                        print(f"❌ [DEBUG] 浏览器在第 {i+1} 秒时连接失败: {str(e)}", flush=True)
                        sys.stdout.flush()
                        raise Exception(f"浏览器连接失败（第{i+1}秒）: {str(e)}")
                
                print(f"✅ [DEBUG] 浏览器稳定检查完成", flush=True)
                sys.stdout.flush()
            
            # 验证浏览器状态
            if not self.browser:
                if self.debug_mode:
                    print(f"❌ [DEBUG] 浏览器启动失败或已断开", flush=True)
                    sys.stdout.flush()
                raise Exception("浏览器启动失败或已断开")
            
            try:
                # 验证浏览器是否仍然有效
                _ = self.browser.contexts
                if self.debug_mode:
                    print(f"🔍 [DEBUG] 浏览器状态验证成功", flush=True)
                    sys.stdout.flush()
            except Exception as e:
                if self.debug_mode:
                    print(f"❌ [DEBUG] 浏览器状态验证失败: {str(e)}", flush=True)
                    sys.stdout.flush()
                raise Exception(f"浏览器在创建页面前已断开: {str(e)}")
            
            # 创建页面，带重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 尝试创建页面（{attempt + 1}/{max_retries}）...", flush=True)
                        sys.stdout.flush()
                    
                    # 在创建页面前，再次检查浏览器状态
                    if not self.browser:
                        if self.debug_mode:
                            print(f"❌ [DEBUG] 浏览器对象为None，无法创建页面", flush=True)
                            sys.stdout.flush()
                        raise Exception("浏览器对象为None")
                    
                    try:
                        _ = self.browser.contexts
                        if self.debug_mode:
                            print(f"🔍 [DEBUG] 浏览器连接正常，准备创建context...", flush=True)
                            sys.stdout.flush()
                    except Exception as e:
                        if self.debug_mode:
                            print(f"❌ [DEBUG] 浏览器连接检查失败: {str(e)}", flush=True)
                            sys.stdout.flush()
                        raise Exception(f"浏览器连接检查失败: {str(e)}")
                    
                    # 在headless=False模式下，创建context前额外等待
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 等待1秒后创建context...", flush=True)
                        sys.stdout.flush()
                        await asyncio.sleep(1)
                    
                    page = await self._create_page()
                    if self.debug_mode:
                        print(f"✅ [DEBUG] 页面已创建成功！", flush=True)
                        sys.stdout.flush()
                    logger.info(f"🔍 [DEBUG] 页面已创建")
                    break
                except Exception as e:
                    error_msg = str(e)
                    if self.debug_mode:
                        print(f"⚠️ [DEBUG] 创建页面失败: {error_msg[:150]}", flush=True)
                        sys.stdout.flush()
                    
                    if attempt < max_retries - 1:
                        if self.debug_mode:
                            print(f"🔍 [DEBUG] 等待3秒后重试... ({attempt + 1}/{max_retries})", flush=True)
                            sys.stdout.flush()
                        await asyncio.sleep(3)
                        # 重新验证浏览器
                        if not self.browser:
                            if self.debug_mode:
                                print(f"❌ [DEBUG] 浏览器已断开，无法重试", flush=True)
                                sys.stdout.flush()
                            raise Exception("浏览器已断开，无法重试")
                    else:
                        if self.debug_mode:
                            print(f"❌ [DEBUG] 创建页面失败，已重试 {max_retries} 次", flush=True)
                            sys.stdout.flush()
                        raise
            
            # 访问Patch主页
            # 工作流程：访问主页 → 输入zipcode → 自动完成建议 → 点击建议 → 跳转到zipcode对应页面 → 提取文章
            home_url = "https://patch.com/"
            if self.debug_mode:
                print(f"🔍 [DEBUG] 步骤1: 访问主页: {home_url}")
            logger.info(f"🔍 [DEBUG] 步骤1: 访问主页: {home_url}")
            
            # 使用更宽松的等待策略，避免超时（与Redfin/Newsbreak保持一致）
            try:
                logger.debug(f"{self.source_name}: 等待页面加载 (domcontentloaded)...")
                await page.goto(home_url, wait_until="domcontentloaded", timeout=30000)
                logger.debug(f"{self.source_name}: 页面DOM已加载")
            except Exception as goto_error:
                # 如果domcontentloaded失败，尝试更宽松的策略
                logger.warning(f"{self.source_name}: domcontentloaded失败，尝试commit: {str(goto_error)[:100]}")
                try:
                    await page.goto(home_url, wait_until="commit", timeout=30000)
                    logger.debug(f"{self.source_name}: 页面导航已提交")
                except Exception as e2:
                    logger.error(f"{self.source_name}: 页面导航完全失败: {str(e2)[:100]}", exc_info=True)
                    raise
            
            await self._random_delay()
            
            # 调试：记录初始URL和页面标题
            initial_url = page.url
            page_title = await page.title()
            if self.debug_mode:
                print(f"🔍 [DEBUG] 初始URL: {initial_url}")
                print(f"🔍 [DEBUG] 页面标题: {page_title}")
            logger.info(f"🔍 [DEBUG] 初始URL: {initial_url}")
            logger.info(f"🔍 [DEBUG] 页面标题: {page_title}")
            await self._take_debug_screenshot(page, "01_initial_page")
            
            # 处理可能的弹窗
            try:
                close_buttons = await page.query_selector_all(
                    "button[aria-label*='close'], button[aria-label*='Close'], .close-button"
                )
                for btn in close_buttons[:1]:
                    try:
                        await btn.click(timeout=2000)
                        await self._random_delay(0.5, 1.0)
                    except Exception as e:
                        logger.debug(f"关闭弹窗失败: {str(e)}")
            except Exception as e:
                logger.debug(f"查找弹窗按钮失败: {str(e)}")
            
            # 步骤2: 查找并输入zipcode到输入框
            if self.debug_mode:
                print(f"🔍 [DEBUG] 步骤2: 查找zipcode输入框 #find-your-patch")
            logger.info(f"🔍 [DEBUG] 步骤2: 查找zipcode输入框 #find-your-patch")
            try:
                # 滚动到页面顶部，确保输入框可见
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.5)  # 等待滚动完成
                
                # 尝试多个选择器，等待输入框出现
                zipcode_input = None
                zipcode_selectors = [
                    "#find-your-patch",
                    "input#find-your-patch",
                    "input[placeholder*='ZIP code' i]",
                    "input[placeholder*='town' i]",
                    ".find-your-patch",
                    "input.find-your-patch"
                ]
                
                for selector in zipcode_selectors:
                    try:
                        zipcode_input = await page.wait_for_selector(selector, timeout=5000, state="visible")
                        if zipcode_input:
                            if self.debug_mode:
                                print(f"🔍 [DEBUG] 找到zipcode输入框: {selector}")
                            logger.info(f"🔍 [DEBUG] 找到zipcode输入框: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"等待选择器 {selector} 超时: {str(e)}")
                        continue
                
                if zipcode_input:
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 找到zipcode输入框，输入zipcode: {zipcode}")
                    logger.info(f"🔍 [DEBUG] 找到zipcode输入框，输入zipcode: {zipcode}")
                    
                    # 输入zipcode前检查浏览器状态
                    if not await self._verify_browser_state(page):
                        logger.warning(f"{self.source_name}: 输入zipcode前浏览器状态检查失败，尝试重新创建")
                        await self.cleanup()
                        await self._setup_browser(headless=True)
                        page = await self._create_page()
                        # 重新访问主页并查找输入框
                        await page.goto("https://patch.com/", wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(1)
                        zipcode_input = await page.wait_for_selector("input[placeholder*='ZIP code' i]", timeout=5000, state="visible")
                        if not zipcode_input:
                            raise Exception("重新创建浏览器后仍无法找到输入框")
                    
                    await zipcode_input.fill(zipcode)
                    # 等待3秒，确保自动完成建议加载完成（基于实际测试）
                    await asyncio.sleep(3)
                    await self._take_debug_screenshot(page, "02_after_input")
                    
                    # 步骤3: 等待并检测自动完成建议
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 步骤3: 等待自动完成建议出现...")
                    logger.info(f"🔍 [DEBUG] 步骤3: 等待自动完成建议出现...")
                    # 使用实际发现的选择器
                    autocomplete_selectors = [
                        ".autocomplete__dropdown",  # 实际发现的容器选择器
                        ".autocomplete__list",      # 列表选择器
                        "[class*='autocomplete']",  # fallback
                        "[class*='dropdown']"       # fallback
                    ]
                    
                    autocomplete_found = False
                    autocomplete_element = None
                    for selector in autocomplete_selectors:
                        try:
                            autocomplete_element = await page.wait_for_selector(selector, timeout=5000, state="visible")
                            if autocomplete_element:
                                if self.debug_mode:
                                    print(f"🔍 [DEBUG] 找到自动完成容器: {selector}")
                                logger.info(f"🔍 [DEBUG] 找到自动完成容器: {selector}")
                                autocomplete_found = True
                                await self._take_debug_screenshot(page, "03_autocomplete_appeared")
                                break
                        except Exception as e:
                            logger.debug(f"等待选择器 {selector} 超时: {str(e)}")
                            continue
                    
                    if not autocomplete_found:
                        logger.warning(f"🔍 [DEBUG] 未找到自动完成建议，等待额外2秒后继续...")
                        await asyncio.sleep(2)
                        await self._take_debug_screenshot(page, "03_no_autocomplete")
                    
                    # 步骤4: 检测自动完成建议项
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 步骤4: 检测自动完成建议项...")
                    logger.info(f"🔍 [DEBUG] 步骤4: 检测自动完成建议项...")
                    # 使用实际发现的选择器
                    suggestion_selectors = [
                        ".autocomplete__list-item a.autocomplete__btn",  # 实际发现的链接选择器
                        ".autocomplete__list-item a",                   # 列表项中的链接
                        ".autocomplete__btn",                           # 按钮选择器
                        ".autocomplete__list-item"                      # 列表项选择器
                    ]
                    
                    suggestions = []
                    for selector in suggestion_selectors:
                        try:
                            suggestions = await page.query_selector_all(selector)
                            if suggestions:
                                if self.debug_mode:
                                    print(f"🔍 [DEBUG] 找到 {len(suggestions)} 个建议项 (选择器: {selector})")
                                logger.info(f"🔍 [DEBUG] 找到 {len(suggestions)} 个建议项 (选择器: {selector})")
                                # 记录建议项文本
                                for i, suggestion in enumerate(suggestions[:5]):  # 只记录前5个
                                    try:
                                        text = await suggestion.inner_text()
                                        if self.debug_mode:
                                            print(f"🔍 [DEBUG]   建议项 {i+1}: {text[:100]}")
                                        logger.info(f"🔍 [DEBUG]   建议项 {i+1}: {text[:100]}")
                                    except Exception:
                                        pass
                                break
                        except Exception as e:
                            logger.debug(f"查询建议项选择器 {selector} 失败: {str(e)}")
                            continue
                    
                    # 步骤5: 获取第一个建议项的URL并导航（避免点击导致的浏览器崩溃）
                    if suggestions:
                        if self.debug_mode:
                            print(f"🔍 [DEBUG] 步骤5: 获取第一个建议项的URL并导航...")
                        logger.info(f"🔍 [DEBUG] 步骤5: 获取第一个建议项的URL并导航...")
                        try:
                            # 获取第一个建议项的URL
                            first_suggestion = suggestions[0]
                            suggestion_url = await first_suggestion.get_attribute("href")
                            suggestion_text = await first_suggestion.inner_text()
                            
                            if not suggestion_url:
                                # 如果没有href，尝试从父元素获取
                                parent = await first_suggestion.query_selector("..")
                                if parent:
                                    suggestion_url = await parent.get_attribute("href")
                            
                            if suggestion_url:
                                # 构建完整URL
                                if suggestion_url.startswith('/'):
                                    target_url = f"https://patch.com{suggestion_url}"
                                elif suggestion_url.startswith('http'):
                                    target_url = suggestion_url
                                else:
                                    target_url = f"https://patch.com/{suggestion_url}"
                                
                                if self.debug_mode:
                                    print(f"🔍 [DEBUG] 建议项文本: {suggestion_text}")
                                    print(f"🔍 [DEBUG] 建议项URL: {suggestion_url}")
                                    print(f"🔍 [DEBUG] 目标URL: {target_url}")
                                logger.info(f"🔍 [DEBUG] 建议项文本: {suggestion_text}")
                                logger.info(f"🔍 [DEBUG] 建议项URL: {suggestion_url}")
                                logger.info(f"🔍 [DEBUG] 目标URL: {target_url}")
                                
                                # 导航到目标URL，带重试机制（最多重试2次）
                                max_navigation_retries = 2
                                navigation_success = False
                                
                                for nav_attempt in range(max_navigation_retries + 1):  # 初始尝试 + 2次重试 = 总共3次
                                    try:
                                        # 导航前检查浏览器状态
                                        if not await self._verify_browser_state(page):
                                            logger.warning(f"{self.source_name}: 导航前浏览器状态检查失败（尝试 {nav_attempt + 1}/{max_navigation_retries + 1}）")
                                            
                                            # 如果浏览器无效且不是最后一次尝试，尝试重新创建
                                            if nav_attempt < max_navigation_retries:
                                                logger.info(f"{self.source_name}: 尝试重新创建浏览器和页面...")
                                                try:
                                                    # 重新创建浏览器和页面
                                                    await self.cleanup()
                                                    await self._setup_browser(headless=True)
                                                    page = await self._create_page()
                                                    
                                                    # 重新访问主页并输入zipcode（简化流程，直接导航到目标URL）
                                                    logger.info(f"{self.source_name}: 浏览器已重新创建，直接导航到目标URL")
                                                except Exception as recreate_error:
                                                    logger.error(f"{self.source_name}: 重新创建浏览器失败: {str(recreate_error)}")
                                                    if nav_attempt == max_navigation_retries:
                                                        raise
                                                    continue
                                            else:
                                                raise Exception("浏览器状态无效且已达到最大重试次数")
                                        
                                        # 执行导航
                                        if nav_attempt == 0:
                                            # 第一次尝试：使用domcontentloaded
                                            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                                        else:
                                            # 重试：使用更宽松的commit策略
                                            logger.info(f"{self.source_name}: 导航重试 {nav_attempt}/{max_navigation_retries}，使用commit策略")
                                            await page.goto(target_url, wait_until="commit", timeout=30000)
                                        
                                        if self.debug_mode:
                                            print(f"🔍 [DEBUG] 已导航到目标URL（尝试 {nav_attempt + 1}）")
                                        logger.info(f"🔍 [DEBUG] 已导航到目标URL（尝试 {nav_attempt + 1}）")
                                        await self._take_debug_screenshot(page, f"04_navigated_to_target_attempt_{nav_attempt + 1}")
                                        
                                        # 等待页面内容加载
                                        await asyncio.sleep(2)  # 等待内容加载
                                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                                        await asyncio.sleep(1)  # 额外等待
                                        
                                        if self.debug_mode:
                                            print(f"🔍 [DEBUG] 目标页面已加载完成")
                                        logger.info(f"🔍 [DEBUG] 目标页面已加载完成")
                                        await self._take_debug_screenshot(page, "05_target_page_loaded")
                                        
                                        navigation_success = True
                                        break
                                        
                                    except Exception as goto_error:
                                        error_msg = str(goto_error)
                                        is_browser_closed = "closed" in error_msg.lower() or "disconnected" in error_msg.lower()
                                        
                                        if nav_attempt < max_navigation_retries:
                                            # 计算重试延迟（指数退避：1秒、2秒）
                                            retry_delay = 2 ** nav_attempt
                                            logger.warning(
                                                f"{self.source_name}: 导航失败（尝试 {nav_attempt + 1}/{max_navigation_retries + 1}），"
                                                f"{retry_delay}秒后重试。错误: {error_msg[:100]}"
                                            )
                                            
                                            if is_browser_closed:
                                                logger.warning(f"{self.source_name}: 检测到浏览器关闭错误，将在重试前重新创建浏览器")
                                            
                                            await asyncio.sleep(retry_delay)
                                        else:
                                            # 最后一次尝试也失败
                                            logger.error(
                                                f"{self.source_name}: 页面导航完全失败（已重试 {max_navigation_retries} 次）。"
                                                f"目标URL: {target_url}，错误类型: {'浏览器关闭' if is_browser_closed else '导航错误'}，"
                                                f"错误信息: {error_msg[:200]}",
                                                exc_info=True
                                            )
                                            raise
                                
                                if not navigation_success:
                                    raise Exception(f"导航失败：经过 {max_navigation_retries + 1} 次尝试后仍无法导航到 {target_url}")
                            else:
                                logger.warning(f"🔍 [DEBUG] 未找到建议项的URL，尝试点击方式...")
                                # 回退到点击方式（但使用更稳定的方法）
                                try:
                                    # 使用page.click而不是element.click，更稳定
                                    selector = ".autocomplete__list-item a.autocomplete__btn"
                                    await page.click(selector, timeout=5000)
                                    await asyncio.sleep(2)
                                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                                    await asyncio.sleep(1)
                                except Exception as click_error:
                                    logger.error(f"🔍 [DEBUG] 点击建议项也失败: {str(click_error)}", exc_info=True)
                                    
                        except Exception as e:
                            logger.error(f"🔍 [DEBUG] 处理建议项失败: {str(e)}", exc_info=True)
                    else:
                        logger.warning(f"🔍 [DEBUG] 未找到建议项，尝试点击搜索按钮...")
                        # 回退到搜索按钮
                        search_button = await page.query_selector("button[type='submit'], input[type='submit']")
                        if not search_button:
                            buttons = await page.query_selector_all("button")
                            for btn in buttons:
                                try:
                                    text = await btn.inner_text()
                                    if text and ('search' in text.lower() or 'find' in text.lower()):
                                        search_button = btn
                                        break
                                except Exception:
                                    continue
                        
                        if search_button:
                            logger.info(f"🔍 [DEBUG] 找到搜索按钮，点击...")
                            await search_button.click()
                            await self._random_delay(2, 4)
                            await self._take_debug_screenshot(page, "04_after_search_button")
                else:
                    logger.warning(f"🔍 [DEBUG] 未找到zipcode输入框")
            except Exception as e:
                logger.error(f"🔍 [DEBUG] 处理zipcode输入框失败: {str(e)}", exc_info=True)
            
            # 步骤6: 在跳转后的页面查找文章列表
            current_url = page.url
            current_title = await page.title()
            if self.debug_mode:
                print(f"🔍 [DEBUG] 步骤6: 在当前页面查找文章列表")
                print(f"🔍 [DEBUG] 当前URL: {current_url}")
                print(f"🔍 [DEBUG] 当前页面标题: {current_title}")
            logger.info(f"🔍 [DEBUG] 步骤6: 在当前页面查找文章列表")
            logger.info(f"🔍 [DEBUG] 当前URL: {current_url}")
            logger.info(f"🔍 [DEBUG] 当前页面标题: {current_title}")
            
            # 等待文章列表加载 - 使用多种备选选择器（优先使用实际发现的选择器）
            article_selectors = [
                "article.styles_ArticleCard__ZF3Wi",  # 实际发现的文章选择器（优先级最高）
                "article.styles_Card__h4UC9",         # 实际发现的文章选择器（优先级最高）
                ".patch-article-card",
                ".article-card",
                "article",
                "[data-testid='article']",
                ".card",
                "div[class*='article']",
                "div[class*='patch']",
                "div[class*='story']",
                "div[class*='post']",
                "main article",
                ".content article",
                ".article-list article",
                ".news-list article"
            ]
            
            # 尝试等待任一选择器
            found_selector = None
            for selector in article_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    found_selector = selector
                    if self.debug_mode:
                        print(f"🔍 [DEBUG] 找到文章列表选择器: {selector}")
                    logger.info(f"🔍 [DEBUG] 找到文章列表选择器: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"等待选择器 {selector} 超时: {str(e)}")
                    continue
            
            # 使用robust方法查找元素
            article_elements = await self.find_elements_with_fallback(page, article_selectors)
            
            if not article_elements or len(article_elements) == 0:
                if self.debug_mode:
                    print(f"🔍 [DEBUG] 未找到文章列表")
                    print(f"🔍 [DEBUG] 当前URL: {current_url}")
                    print(f"🔍 [DEBUG] 当前页面标题: {current_title}")
                logger.warning(f"🔍 [DEBUG] 未找到文章列表")
                logger.warning(f"🔍 [DEBUG] 当前URL: {current_url}")
                logger.warning(f"🔍 [DEBUG] 当前页面标题: {current_title}")
                
                # 调试：尝试查找所有可能的文章容器
                if self.debug_mode:
                    print(f"🔍 [DEBUG] 尝试查找所有可能的文章容器...")
                logger.info(f"🔍 [DEBUG] 尝试查找所有可能的文章容器...")
                all_articles = await page.query_selector_all("article")
                all_cards = await page.query_selector_all(".card, [class*='card']")
                all_links = await page.query_selector_all("a[href*='/news'], a[href*='/article'], a[href*='/story']")
                
                if self.debug_mode:
                    print(f"🔍 [DEBUG] 找到 {len(all_articles)} 个 <article> 元素")
                    print(f"🔍 [DEBUG] 找到 {len(all_cards)} 个 .card 元素")
                    print(f"🔍 [DEBUG] 找到 {len(all_links)} 个新闻链接")
                logger.info(f"🔍 [DEBUG] 找到 {len(all_articles)} 个 <article> 元素")
                logger.info(f"🔍 [DEBUG] 找到 {len(all_cards)} 个 .card 元素")
                logger.info(f"🔍 [DEBUG] 找到 {len(all_links)} 个新闻链接")
                
                await self._take_debug_screenshot(page, "06_no_articles_found")
            else:
                if self.debug_mode:
                    print(f"🔍 [DEBUG] 找到 {len(article_elements)} 个文章元素 (使用选择器: {found_selector})")
                logger.info(f"🔍 [DEBUG] 找到 {len(article_elements)} 个文章元素 (使用选择器: {found_selector})")
                await self._take_debug_screenshot(page, "06_articles_found")
            
            for i, element in enumerate(article_elements[:limit]):
                try:
                    article = await self._extract_article_data(element, zipcode)
                    if article:
                        if self.debug_mode:
                            print(f"🔍 [DEBUG] 提取文章 {i+1}:")
                            print(f"  - 标题: {article.get('title', '')[:80]}")
                            print(f"  - URL: {article.get('url', '')[:80]}")
                            print(f"  - 日期: {article.get('publish_date', '')}")
                            print(f"  - 摘要: {article.get('content_summary', '')[:80]}")
                        logger.debug(f"提取文章 {i+1}: 标题={article.get('title', '')[:50]}, URL={article.get('url', '')[:50]}")
                        articles.append(article)
                        await self._random_delay(0.3, 0.8)
                    else:
                        if self.debug_mode:
                            print(f"⚠️ [DEBUG] 文章 {i+1} 提取失败（返回None）")
                        logger.warning(f"文章 {i+1} 提取失败（返回None）")
                except Exception as e:
                    logger.warning(f"提取第 {i+1} 篇文章失败: {str(e)}", exc_info=True)
                    continue
            
        except Exception as e:
            if self.debug_mode:
                print(f"❌ [DEBUG] Patch采集过程出错: {str(e)}")
                import traceback
                traceback.print_exc()
            logger.error(f"Patch采集过程出错: {str(e)}", exc_info=True)
        finally:
            # 确保页面和浏览器资源都被清理
            # 注意：不需要单独关闭page，cleanup()会关闭整个context（包括所有页面）
            await self.cleanup()
        
        return articles
    
    async def extract_article_data_robust(self, element, zipcode: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        使用Patch特定的选择器提取文章数据
        优先使用Patch框架的精确选择器，失败后回退到通用fallback
        
        Args:
            element: 文章元素
            zipcode: 邮政编码
            
        Returns:
            文章数据字典
        """
        try:
            # 标题 - 优先使用Patch特定选择器
            title = await self.find_element_with_fallback(
                element,
                [
                    "h2.styles_Card__Title__cEqF8 a",  # Patch特定选择器（标题链接）
                    "h2.styles_Card__Title__cEqF8",    # Patch特定选择器（标题文本）
                    "h1", "h2", "h3", "h4",           # 通用fallback
                    ".title", ".headline", ".article-title", ".post-title",
                    "[data-testid*='title']",
                    "a[href] > *:first-child",
                    "a.title", "a.headline"
                ]
            )
            
            # 链接 - 优先使用Patch特定选择器
            link_elem = await self.find_element_with_fallback(
                element,
                [
                    "a.styles_Card__TitleLink__Df5jx",  # Patch特定选择器（标题链接）
                    "h2.styles_Card__Title__cEqF8 a",  # Patch特定选择器（标题中的链接）
                    "a[href]",                          # 通用链接
                    "a.article-link",
                    "a[href*='/news']",
                    "a[href*='/article']",
                    "a[href*='/story']",
                    ".title a",
                    ".headline a"
                ],
                extract_text=False
            )
            
            url = ""
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    url = href
            
            # 日期 - 优先使用Patch特定选择器
            date_elem = await self.find_element_with_fallback(
                element,
                [
                    "time[datetime]",                              # datetime属性（优先级最高）
                    ".styles_Card__LabelWrapper__e_6qr time",       # Patch特定选择器（标签包装器中的time）
                    "time",
                    ".date", ".publish-date", ".published-date",
                    "[datetime]",
                    ".timestamp",
                    "[data-testid*='date']",
                    ".meta time",
                    ".byline time"
                ],
                extract_text=False
            )
            
            publish_date = None
            if date_elem:
                datetime_attr = await date_elem.get_attribute("datetime")
                if datetime_attr:
                    publish_date = datetime_attr
                else:
                    date_text = await date_elem.inner_text()
                    if date_text:
                        publish_date = date_text.strip()
            
            # 摘要 - 优先使用Patch特定选择器
            summary = await self.find_element_with_fallback(
                element,
                [
                    "p.styles_Card__Description__kWZTu",  # Patch特定选择器（描述段落）
                    ".summary", ".excerpt", ".description",
                    ".article-summary", ".post-excerpt",
                    "p:not(.title):not(.headline)",
                    ".snippet", ".preview"
                ]
            )
            
            # 验证必需字段
            if not title or not url:
                # 如果特定选择器失败，回退到通用方法
                logger.debug("Patch特定选择器失败，回退到通用fallback")
                return await super().extract_article_data_robust(element, zipcode)
            
            return {
                "title": title,
                "url": url,
                "publish_date": publish_date or "",
                "content": summary or "",
                "content_summary": summary or "",
                "keywords": [],
                "zipcode": zipcode if zipcode else None
            }
            
        except Exception as e:
            logger.warning(f"Patch特定选择器提取失败: {str(e)}，回退到通用方法")
            return await super().extract_article_data_robust(element, zipcode)
    
    async def _extract_article_data(self, element, zipcode: str) -> Dict[str, Any]:
        """
        从文章元素中提取数据（使用健壮的多选择器机制）
        
        Args:
            element: Playwright元素
            zipcode: Zipcode
            
        Returns:
            文章数据字典
        """
        try:
            # 使用robust mixin提取数据（会调用重写的extract_article_data_robust）
            article_data = await self.extract_article_data_robust(element, zipcode)
            
            if not article_data:
                return None
            
            # 处理URL（相对URL转换为绝对URL）
            url = article_data.get('url', '')
            if url and not url.startswith('http'):
                url = f"https://patch.com{url}" if url.startswith('/') else f"https://patch.com/{url}"
                if self.debug_mode:
                    logger.debug(f"URL已转换为绝对URL: {url}")
            
            # 解析日期（优先使用datetime属性，然后是文本内容）
            publish_date = article_data.get('publish_date', '')
            if publish_date:
                # 如果已经是ISO格式（从datetime属性获取），直接使用
                if 'T' in publish_date and ('Z' in publish_date or '+' in publish_date or '-' in publish_date[-6:]):
                    # 已经是ISO格式
                    parsed_date = publish_date
                else:
                    # 需要解析相对时间或文本日期
                    parsed_date = self._parse_date(publish_date)
                if self.debug_mode:
                    logger.debug(f"日期解析: {publish_date} -> {parsed_date}")
                publish_date = parsed_date
            else:
                publish_date = datetime.utcnow().isoformat()
                if self.debug_mode:
                    logger.debug(f"未找到日期，使用当前时间: {publish_date}")
            
            return {
                "source": self.source_name,
                "zipcode": zipcode,
                "title": article_data.get('title', ''),
                "url": url,
                "publish_date": publish_date,
                "content": article_data.get('content', ''),
                "content_summary": article_data.get('content_summary', ''),
                "keywords": article_data.get('keywords', [])
            }
            
        except Exception as e:
            logger.warning(f"提取文章数据失败: {str(e)}")
            return None
    
    def _parse_date(self, date_str: str) -> str:
        """
        解析日期字符串为ISO格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            ISO格式日期字符串
        """
        if not date_str:
            return datetime.utcnow().isoformat()
        
        date_str = date_str.strip().lower()
        now = datetime.utcnow()
        
        # 处理相对时间（与NewsbreakScraper相同的逻辑）
        if "just now" in date_str or "now" in date_str:
            return now.isoformat()
        elif "minute" in date_str:
            # 优化：缓存re.search结果，避免重复调用
            match = re.search(r'(\d+)', date_str)
            minutes = int(match.group(1)) if match else 0
            return (now - timedelta(minutes=minutes)).isoformat()
        elif "hour" in date_str:
            # 优化：缓存re.search结果，避免重复调用
            match = re.search(r'(\d+)', date_str)
            hours = int(match.group(1)) if match else 0
            return (now - timedelta(hours=hours)).isoformat()
        elif "day" in date_str or "yesterday" in date_str:
            # 优化：缓存re.search结果，避免重复调用
            days = 1 if "yesterday" in date_str else (int((match := re.search(r'(\d+)', date_str)).group(1)) if match else 1)
            return (now - timedelta(days=days)).isoformat()
        else:
            try:
                from dateutil import parser
                parsed_date = parser.parse(date_str)
                return parsed_date.isoformat()
            except Exception as e:
                logger.debug(f"日期解析失败: {date_str} - {str(e)}")
                return now.isoformat()
