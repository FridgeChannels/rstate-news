"""
Newsbreak采集器
采集基于Zipcode的局部新闻
"""
import asyncio
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from scrapers.local_news_scraper import LocalNewsScraper
from scrapers.robust_scraper_mixin import RobustScraperMixin
from utils.logger import logger


class NewsbreakScraper(LocalNewsScraper, RobustScraperMixin):
    """Newsbreak新闻采集器"""
    
    def __init__(self):
        super().__init__("Newsbreak")
    
    async def _extract_json_data(self, page) -> Optional[Dict[str, Any]]:
        """
        从页面中提取__NEXT_DATA__ JSON数据
        
        Args:
            page: Playwright页面对象
            
        Returns:
            JSON数据字典，如果提取失败返回None
        """
        try:
            # 查找__NEXT_DATA__脚本标签
            next_data_script = await page.query_selector('script#__NEXT_DATA__')
            if not next_data_script:
                logger.debug("未找到__NEXT_DATA__脚本标签")
                return None
            
            # 获取脚本内容
            script_content = await next_data_script.inner_text()
            if not script_content:
                logger.debug("__NEXT_DATA__脚本内容为空")
                return None
            
            # 解析JSON
            next_data = json.loads(script_content)
            
            # 提取feed数据
            if 'props' in next_data and 'pageProps' in next_data['props']:
                page_props = next_data['props']['pageProps']
                if 'feed' in page_props:
                    feed = page_props['feed']
                    if feed and len(feed) > 0:
                        logger.debug(f"从JSON中提取到 {len(feed)} 篇文章")
                        return {'feed': feed, 'next_data': next_data}
            
            logger.debug("JSON中未找到feed数据")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"解析__NEXT_DATA__ JSON失败: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"提取__NEXT_DATA__ JSON失败: {str(e)}")
            return None
    
    async def _scrape_zipcode_news(self, zipcode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        采集Newsbreak的Zipcode新闻
        新流程：通过locations页面选择城市，然后并行采集三个分类（business/education/poi_housing）
        
        Args:
            zipcode: 邮政编码
            limit: 采集数量限制
            
        Returns:
            文章列表（已去重，只包含24小时内的文章）
        """
        articles = []
        page = None
        
        try:
            logger.info(f"{self.source_name}: 开始采集Zipcode {zipcode} 的新闻")
            await self._setup_browser(headless=True)
            
            # 再次验证浏览器是否有效
            if not self.browser:
                raise Exception("浏览器启动失败")
            
            page = await self._create_page()
            
            # 验证页面是否有效
            if not page:
                raise Exception("页面创建失败")
            
            # Step 1: 访问locations页面并选择城市
            city_url = await self._select_city_by_zipcode(page, zipcode)
            if not city_url:
                logger.warning(f"{self.source_name}: 无法找到zipcode {zipcode} 对应的城市页面，跳过")
                return []
            
            logger.info(f"{self.source_name}: 找到城市URL: {city_url}")
            
            # Step 2: 并行采集三个分类（每个分类使用独立的页面）
            categories = ['business', 'education', 'poi_housing']
            
            async def scrape_category_with_page(category: str):
                """为每个分类创建独立页面并采集"""
                category_page = None
                try:
                    # 为每个分类创建新页面，避免并发冲突
                    category_page = await self._create_page()
                    return await self._scrape_category(category_page, city_url, category, zipcode, limit)
                except Exception as e:
                    logger.warning(f"{self.source_name}: 分类 {category} 采集异常: {str(e)}")
                    return []
                finally:
                    # 关闭分类页面（但不关闭context）
                    if category_page:
                        try:
                            await category_page.close()
                        except Exception:
                            pass
            
            category_results = await asyncio.gather(
                *[scrape_category_with_page(category) for category in categories],
                return_exceptions=True
            )
            
            # Step 3: 合并结果并处理异常
            all_articles = []
            for i, result in enumerate(category_results):
                category = categories[i]
                if isinstance(result, Exception):
                    logger.warning(f"{self.source_name}: 分类 {category} 采集失败: {str(result)}")
                    continue
                elif isinstance(result, list):
                    logger.info(f"{self.source_name}: 分类 {category} 采集到 {len(result)} 篇文章")
                    all_articles.extend(result)
                else:
                    logger.warning(f"{self.source_name}: 分类 {category} 返回了意外的结果类型: {type(result)}")
            
            # Step 4: 去重（基于URL）
            articles = self._deduplicate_articles(all_articles)
            logger.info(f"{self.source_name}: 去重后剩余 {len(articles)} 篇文章")
            
            # Step 5: 24小时过滤
            articles = self._filter_24_hours(articles)
            logger.info(f"{self.source_name}: 24小时过滤后剩余 {len(articles)} 篇文章")
            
            # 限制数量
            if len(articles) > limit:
                articles = articles[:limit]
                logger.info(f"{self.source_name}: 限制数量后剩余 {len(articles)} 篇文章")
            
        except Exception as e:
            logger.error(f"Newsbreak采集过程出错: {str(e)}", exc_info=True)
        finally:
            # 确保页面和浏览器资源都被清理
            await self.cleanup()
        
        return articles
    
    async def _verify_browser_state_newsbreak(self, page) -> bool:
        """
        验证浏览器状态（Newsbreak专用）
        
        Args:
            page: Playwright页面对象
            
        Returns:
            True如果浏览器状态有效，False否则
        """
        try:
            if not self.browser:
                return False
            try:
                _ = self.browser.contexts
            except Exception:
                return False
            if not page:
                return False
            try:
                _ = page.url
            except Exception:
                return False
            return True
        except Exception:
            return False
    
    async def _select_city_by_zipcode(self, page, zipcode: str) -> Optional[str]:
        """
        通过locations页面选择zipcode对应的城市
        
        Args:
            page: Playwright页面对象
            zipcode: 邮政编码
            
        Returns:
            城市URL（如 '/beverly-hills-ca'），如果找不到返回None
        """
        try:
            # 访问locations页面
            locations_url = "https://www.newsbreak.com/locations"
            logger.info(f"{self.source_name}: 访问locations页面: {locations_url}")
            
            await page.goto(locations_url, wait_until="domcontentloaded", timeout=30000)
            await self._random_delay(1, 2)
            
            # 处理可能的弹窗
            try:
                close_buttons = await page.query_selector_all(
                    "button[aria-label*='close'], button[aria-label*='Close'], .close-button, [data-testid='close']"
                )
                for btn in close_buttons[:1]:
                    try:
                        await btn.click(timeout=2000)
                        await self._random_delay(0.5, 1.0)
                    except Exception:
                        pass
            except Exception:
                pass
            
            # 查找输入框（带重试）
            input_selector = 'input[placeholder="City name or zip code"]'
            zipcode_input = None
            max_input_retries = 2
            
            for input_attempt in range(max_input_retries + 1):
                try:
                    # 检查浏览器状态
                    if not await self._verify_browser_state_newsbreak(page):
                        if input_attempt < max_input_retries:
                            logger.warning(f"{self.source_name}: 输入前浏览器状态检查失败，重新创建（尝试 {input_attempt + 1}/{max_input_retries + 1}）")
                            await self.cleanup()
                            await self._setup_browser(headless=True)
                            page = await self._create_page()
                            await page.goto(locations_url, wait_until="domcontentloaded", timeout=30000)
                            await self._random_delay(1, 2)
                            continue
                        else:
                            logger.error(f"{self.source_name}: 浏览器状态检查失败，已达到最大重试次数")
                            return None
                    
                    zipcode_input = await page.wait_for_selector(input_selector, timeout=10000, state="visible")
                    if zipcode_input:
                        break
                except Exception as e:
                    if input_attempt < max_input_retries:
                        logger.warning(f"{self.source_name}: 查找输入框失败，重试: {str(e)[:100]}")
                        await asyncio.sleep(1)
                        continue
                    else:
                        logger.warning(f"{self.source_name}: 未找到zipcode输入框: {str(e)}")
                        return None
            
            if not zipcode_input:
                logger.warning(f"{self.source_name}: 无法找到zipcode输入框")
                return None
            
            # 输入zipcode（带重试机制）
            max_input_retries = 2
            input_success = False
            
            for input_attempt in range(max_input_retries + 1):
                try:
                    # 检查浏览器状态
                    if not await self._verify_browser_state_newsbreak(page):
                        if input_attempt < max_input_retries:
                            logger.warning(f"{self.source_name}: 输入前浏览器状态检查失败，重新创建（尝试 {input_attempt + 1}/{max_input_retries + 1}）")
                            await self.cleanup()
                            await self._setup_browser(headless=True)
                            page = await self._create_page()
                            await page.goto(locations_url, wait_until="domcontentloaded", timeout=30000)
                            await self._random_delay(1, 2)
                            # 重新查找输入框
                            zipcode_input = await page.wait_for_selector(input_selector, timeout=10000, state="visible")
                            continue
                        else:
                            logger.error(f"{self.source_name}: 浏览器状态检查失败，已达到最大重试次数")
                            return None
                    
                    # 先点击输入框，确保获得焦点
                    try:
                        await zipcode_input.click(timeout=3000)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"{self.source_name}: 点击输入框失败: {str(e)}")
                    
                    # 滚动到输入框，确保它在视口中
                    try:
                        await zipcode_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"{self.source_name}: 滚动到输入框失败: {str(e)}")
                    
                    # 清空输入框（如果有内容）
                    try:
                        await zipcode_input.fill("")
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass
                    
                    # 尝试使用fill而不是type，避免触发某些检测机制
                    # 如果fill失败，再尝试type
                    try:
                        await zipcode_input.fill(zipcode)
                        await asyncio.sleep(2)  # 等待自动完成建议出现
                        logger.debug(f"{self.source_name}: 使用fill方法输入zipcode成功")
                    except Exception as fill_error:
                        logger.debug(f"{self.source_name}: fill方法失败，尝试type: {str(fill_error)[:50]}")
                        # 如果fill失败，尝试type
                        await zipcode_input.type(zipcode, delay=200)  # 更慢的输入速度
                        await asyncio.sleep(2)  # 等待自动完成建议出现
                    
                    input_success = True
                    break
                    
                except Exception as input_error:
                    error_msg = str(input_error)
                    is_browser_closed = "closed" in error_msg.lower() or "disconnected" in error_msg.lower()
                    
                    if input_attempt < max_input_retries:
                        retry_delay = 2 ** input_attempt
                        logger.warning(
                            f"{self.source_name}: 输入zipcode失败（尝试 {input_attempt + 1}/{max_input_retries + 1}），"
                            f"{retry_delay}秒后重试。错误: {error_msg[:100]}"
                        )
                        await asyncio.sleep(retry_delay)
                        
                        if is_browser_closed:
                            # 重新创建浏览器和页面
                            try:
                                await self.cleanup()
                            except Exception:
                                pass
                            await self._setup_browser(headless=True)
                            page = await self._create_page()
                            await page.goto(locations_url, wait_until="domcontentloaded", timeout=30000)
                            await self._random_delay(1, 2)
                            # 重新查找输入框
                            try:
                                zipcode_input = await page.wait_for_selector(input_selector, timeout=10000, state="visible")
                            except Exception:
                                logger.error(f"{self.source_name}: 重新创建后仍无法找到输入框")
                                return None
                    else:
                        logger.error(f"{self.source_name}: 输入zipcode完全失败: {error_msg[:200]}")
                        raise
            
            if not input_success:
                logger.error(f"{self.source_name}: 输入zipcode失败：经过 {max_input_retries + 1} 次尝试后仍无法输入")
                return None
            
            # 额外触发事件确保自动完成被触发
            try:
                await zipcode_input.evaluate("element => { element.dispatchEvent(new Event('input', { bubbles: true })); }")
                await asyncio.sleep(0.5)
                await zipcode_input.evaluate("element => { element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: '0' })); }")
                await asyncio.sleep(1)
            except Exception as e:
                logger.debug(f"{self.source_name}: 触发输入事件失败: {str(e)}")
            
            # 根据用户提供的HTML结构，使用更准确的选择器
            # 容器: <div class="jsx-3294552676 absolute text-base ...">
            # 链接: <a aria-label="/beverly-hills-ca" ... href="/beverly-hills-ca">Beverly Hills, CA</a>
            container_selectors = [
                "div[class*='absolute'][class*='text-base']",  # 根据用户提供的HTML
                "div[class*='absolute']",  # 更通用的选择器
                "div[class*='autocomplete']",
                ".autocomplete__list",
                "[class*='autocomplete']"
            ]
            
            suggestion_selectors = [
                "a[href^='/'][aria-label^='/']",  # 根据用户提供的HTML：href和aria-label都以/开头
                "a[href^='/']",  # 更通用的选择器
                "div[class*='px-4'] a",  # 根据用户提供的HTML结构
                ".autocomplete__list-item a.autocomplete__btn",
                ".autocomplete__list-item a",
                "a.autocomplete__btn",
                "[class*='autocomplete'] a"
            ]
            
            first_suggestion = None
            
            # 策略1: 先等待容器出现，再查找链接
            container_found = False
            for container_selector in container_selectors:
                try:
                    # 使用attached状态而不是visible，因为元素可能在视口外
                    await page.wait_for_selector(container_selector, timeout=10000, state="attached")
                    logger.debug(f"{self.source_name}: 自动完成容器已出现: {container_selector}")
                    container_found = True
                    await asyncio.sleep(1)  # 等待内容渲染
                    break
                except Exception as e:
                    logger.debug(f"{self.source_name}: 容器选择器 {container_selector} 等待超时: {str(e)[:80]}")
                    continue
            
            # 策略2: 查找建议链接
            if container_found:
                logger.debug(f"{self.source_name}: 容器已找到，开始查找建议链接...")
                for selector in suggestion_selectors:
                    try:
                        suggestions = await page.query_selector_all(selector)
                        if suggestions and len(suggestions) > 0:
                            # 验证链接是否有效（href以/开头）
                            for suggestion in suggestions:
                                try:
                                    href = await suggestion.get_attribute("href")
                                    if href and href.startswith("/") and len(href) > 1:
                                        first_suggestion = suggestion
                                        logger.info(f"{self.source_name}: 使用选择器找到建议项: {selector} (href: {href})")
                                        break
                                except Exception:
                                    continue
                            if first_suggestion:
                                break
                    except Exception as e:
                        logger.debug(f"{self.source_name}: 建议选择器 {selector} 失败: {str(e)[:50]}")
                        continue
            
            # 策略3: 如果容器未找到，直接尝试查找链接（可能容器选择器不对）
            if not first_suggestion:
                logger.debug(f"{self.source_name}: 容器未找到或链接未找到，直接尝试所有建议选择器...")
                for selector in suggestion_selectors:
                    try:
                        suggestions = await page.query_selector_all(selector)
                        if suggestions and len(suggestions) > 0:
                            # 验证链接是否有效
                            for suggestion in suggestions:
                                try:
                                    href = await suggestion.get_attribute("href")
                                    if href and href.startswith("/") and len(href) > 1:
                                        first_suggestion = suggestion
                                        logger.info(f"{self.source_name}: 直接找到建议项: {selector} (href: {href})")
                                        break
                                except Exception:
                                    continue
                            if first_suggestion:
                                break
                    except Exception as e:
                        logger.debug(f"{self.source_name}: 直接选择器 {selector} 失败: {str(e)[:50]}")
                        continue
            
            # 策略4: 如果还是找不到，等待更长时间并再次尝试
            if not first_suggestion:
                logger.debug(f"{self.source_name}: 等待额外5秒后再次尝试...")
                await asyncio.sleep(5)
                for selector in suggestion_selectors:
                    try:
                        suggestions = await page.query_selector_all(selector)
                        if suggestions and len(suggestions) > 0:
                            for suggestion in suggestions:
                                try:
                                    href = await suggestion.get_attribute("href")
                                    if href and href.startswith("/") and len(href) > 1:
                                        first_suggestion = suggestion
                                        logger.info(f"{self.source_name}: 延迟后找到建议项: {selector} (href: {href})")
                                        break
                                except Exception:
                                    continue
                            if first_suggestion:
                                break
                    except Exception as e:
                        logger.debug(f"{self.source_name}: 延迟选择器 {selector} 失败: {str(e)[:50]}")
                        continue
            
            if not first_suggestion:
                logger.warning(f"{self.source_name}: 未找到自动完成建议项，已尝试所有选择器")
                # 尝试截图以便调试
                try:
                    screenshot_path = Path("logs/newsbreak_debug_screenshot.png")
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"{self.source_name}: 已保存调试截图: {screenshot_path}")
                except Exception:
                    pass
                
                # 尝试获取页面HTML以便调试
                try:
                    html_content = await page.content()
                    html_path = Path("logs/newsbreak_debug_html.html")
                    html_path.parent.mkdir(parents=True, exist_ok=True)
                    html_path.write_text(html_content, encoding='utf-8')
                    logger.info(f"{self.source_name}: 已保存调试HTML: {html_path}")
                except Exception:
                    pass
                
                return None
            
            # 获取第一个建议项的href
            try:
                city_url = await first_suggestion.get_attribute("href")
                if not city_url:
                    # 如果href无效，尝试从aria-label获取
                    aria_label = await first_suggestion.get_attribute("aria-label")
                    if aria_label and aria_label.startswith("/"):
                        logger.info(f"{self.source_name}: 从aria-label找到城市URL: {aria_label}")
                        return aria_label
                    else:
                        logger.warning(f"{self.source_name}: 建议项没有href和aria-label属性")
                        return None
                
                # 确保URL格式正确（应该是相对路径，如 '/beverly-hills-ca'）
                if city_url.startswith('http'):
                    # 如果是绝对URL，提取路径部分
                    from urllib.parse import urlparse
                    parsed = urlparse(city_url)
                    city_url = parsed.path
                
                logger.info(f"{self.source_name}: 找到城市URL: {city_url}")
                return city_url
            except Exception as e:
                logger.warning(f"{self.source_name}: 获取href失败: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"{self.source_name}: 选择城市失败: {str(e)}", exc_info=True)
            return None
    
    async def _scrape_category(self, category_page, city_url: str, category: str, zipcode: str, limit: int) -> List[Dict[str, Any]]:
        """
        采集指定分类的文章
        
        Args:
            category_page: Playwright页面对象（该分类的独立页面）
            city_url: 城市URL（如 '/beverly-hills-ca'）
            category: 分类名称（'business', 'education', 'poi_housing'）
            zipcode: 邮政编码
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        articles = []
        
        try:
            # 构建分类URL
            category_url = f"https://www.newsbreak.com{city_url}-{category}"
            logger.info(f"{self.source_name}: 采集分类 {category}，URL: {category_url}")
            
            # 导航到分类页面（带重试机制）
            max_nav_retries = 2
            nav_success = False
            
            for nav_attempt in range(max_nav_retries + 1):
                try:
                    # 检查页面状态
                    try:
                        _ = category_page.url
                    except Exception:
                        logger.warning(f"{self.source_name}: 分类 {category} 页面已关闭，尝试重新创建（尝试 {nav_attempt + 1}/{max_nav_retries + 1}）")
                        if nav_attempt < max_nav_retries:
                            # 重新创建页面
                            try:
                                await category_page.close()
                            except Exception:
                                pass
                            category_page = await self._create_page()
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception("页面已关闭且无法重新创建")
                    
                    # 执行导航
                    if nav_attempt == 0:
                        await category_page.goto(category_url, wait_until="domcontentloaded", timeout=30000)
                    else:
                        logger.info(f"{self.source_name}: 分类 {category} 导航重试 {nav_attempt}/{max_nav_retries}，使用commit策略")
                        await category_page.goto(category_url, wait_until="commit", timeout=30000)
                    
                    nav_success = True
                    break
                    
                except Exception as nav_error:
                    error_msg = str(nav_error)
                    is_browser_closed = "closed" in error_msg.lower() or "disconnected" in error_msg.lower()
                    
                    if nav_attempt < max_nav_retries:
                        retry_delay = 2 ** nav_attempt
                        logger.warning(
                            f"{self.source_name}: 分类 {category} 导航失败（尝试 {nav_attempt + 1}/{max_nav_retries + 1}），"
                            f"{retry_delay}秒后重试。错误: {error_msg[:100]}"
                        )
                        await asyncio.sleep(retry_delay)
                        
                        if is_browser_closed:
                            # 重新创建页面
                            try:
                                await category_page.close()
                            except Exception:
                                pass
                            category_page = await self._create_page()
                    else:
                        logger.error(f"{self.source_name}: 分类 {category} 导航完全失败: {error_msg[:200]}")
                        raise
            
            if not nav_success:
                raise Exception(f"分类 {category} 导航失败：经过 {max_nav_retries + 1} 次尝试后仍无法导航")
            
            await self._random_delay(1, 2)
            
            # 处理可能的弹窗
            try:
                close_buttons = await category_page.query_selector_all(
                    "button[aria-label*='close'], button[aria-label*='Close'], .close-button, [data-testid='close']"
                )
                for btn in close_buttons[:1]:
                    try:
                        await btn.click(timeout=2000)
                        await self._random_delay(0.5, 1.0)
                    except Exception:
                        pass
            except Exception:
                pass
            
            # 等待文章列表加载
            await asyncio.sleep(2)
            
            # 查找文章容器（使用提供的HTML结构，带重试）
            article_containers = []
            article_selectors = [
                "section.my-1",
                "section.my-1.md\\:my-2",
                "div.flex.flex-col section",
                "section[class*='my-']",
                "article",
                "div[class*='article']"
            ]
            
            for selector in article_selectors:
                try:
                    # 检查页面是否仍然有效
                    try:
                        _ = category_page.url
                    except Exception:
                        logger.warning(f"{self.source_name}: 分类 {category} 页面在查询文章时已关闭")
                        break
                    
                    article_containers = await category_page.query_selector_all(selector)
                    if article_containers:
                        logger.debug(f"{self.source_name}: 分类 {category} 使用选择器 {selector} 找到 {len(article_containers)} 个容器")
                        break
                except Exception as e:
                    logger.debug(f"{self.source_name}: 分类 {category} 选择器 {selector} 失败: {str(e)[:50]}")
                    continue
            
            if not article_containers:
                logger.warning(f"{self.source_name}: 分类 {category} 未找到文章容器")
                return []
            
            logger.info(f"{self.source_name}: 分类 {category} 找到 {len(article_containers)} 个文章容器")
            
            # 提取文章数据
            for i, container in enumerate(article_containers[:limit * 2]):  # 多取一些，因为可能有些无效
                try:
                    article = await self._extract_article_from_html(container, zipcode, city_url)
                    if article:
                        articles.append(article)
                        if len(articles) >= limit:
                            break
                except Exception as e:
                    logger.debug(f"{self.source_name}: 提取分类 {category} 第 {i+1} 篇文章失败: {str(e)}")
                    continue
            
            logger.info(f"{self.source_name}: 分类 {category} 成功提取 {len(articles)} 篇文章")
            
        except Exception as e:
            logger.warning(f"{self.source_name}: 采集分类 {category} 失败: {str(e)}", exc_info=True)
        
        return articles
    
    async def _extract_article_from_html(self, container, zipcode: str, city_url: str) -> Optional[Dict[str, Any]]:
        """
        从HTML容器中提取文章数据
        
        Args:
            container: 文章容器元素
            zipcode: 邮政编码
            city_url: 城市URL（用于提取城市名称）
            
        Returns:
            文章数据字典
        """
        try:
            # 提取标题（h3.text-xl）
            title_elem = await container.query_selector("h3.text-xl")
            if not title_elem:
                return None
            
            title = await title_elem.inner_text()
            if not title or not title.strip():
                return None
            
            # 提取链接（a[aria-label*="/"]）
            link_elem = await container.query_selector('a[aria-label*="/"]')
            if not link_elem:
                return None
            
            url = await link_elem.get_attribute("href")
            if not url:
                return None
            
            # 确保URL是绝对URL
            if url.startswith('/'):
                url = f"https://www.newsbreak.com{url}"
            elif not url.startswith('http'):
                url = f"https://www.newsbreak.com/{url}"
            
            # 提取摘要（p.text-base.text-gray-light）
            summary_elem = await container.query_selector("p.text-base.text-gray-light")
            summary = ""
            if summary_elem:
                summary = await summary_elem.inner_text()
            
            # 提取时间（相对时间文本，如"5小时"）
            time_elem = await container.query_selector("div.text-gray-light.text-sm")
            publish_date = None
            if time_elem:
                time_text = await time_elem.inner_text()
                if time_text:
                    publish_date = self._parse_date(time_text)
            
            # 如果没有提取到时间，使用当前时间
            if not publish_date:
                publish_date = datetime.utcnow().isoformat()
            
            # 从city_url提取城市名称（如 '/beverly-hills-ca' -> 'Beverly Hills'）
            city = ""
            if city_url:
                # 移除前导斜杠，分割并处理
                city_parts = city_url.lstrip('/').split('/')
                if city_parts:
                    city_name = city_parts[-1].replace('-', ' ').title()
                    city = city_name
            
            return {
                "source": self.source_name,
                "zipcode": zipcode,
                "city": city,
                "title": title.strip(),
                "url": url,
                "publish_date": publish_date,
                "content": summary.strip() if summary else "",
                "content_summary": summary.strip() if summary else "",
                "keywords": []
            }
            
        except Exception as e:
            logger.debug(f"{self.source_name}: 从HTML提取文章数据失败: {str(e)}")
            return None
    
    def _deduplicate_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于URL去重文章列表
        
        Args:
            articles: 文章列表
            
        Returns:
            去重后的文章列表（保留第一次出现的）
        """
        seen_urls = set()
        deduplicated = []
        
        for article in articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(article)
        
        return deduplicated
    
    def _filter_24_hours(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤掉超过24小时的文章
        
        Args:
            articles: 文章列表
            
        Returns:
            过滤后的文章列表（只包含24小时内的）
        """
        filtered = []
        now = datetime.now(timezone.utc)  # 使用offset-aware时间
        cutoff_time = now - timedelta(hours=24)
        
        for article in articles:
            publish_date_str = article.get('publish_date')
            if not publish_date_str:
                # 如果没有发布日期，跳过
                continue
            
            try:
                # 解析日期
                if isinstance(publish_date_str, str):
                    # 尝试解析ISO格式
                    try:
                        publish_date = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                    except ValueError:
                        # 如果ISO解析失败，使用dateutil
                        from dateutil import parser
                        publish_date = parser.parse(publish_date_str)
                else:
                    publish_date = publish_date_str
                
                # 确保publish_date是offset-aware
                if publish_date.tzinfo is None:
                    # 假设是UTC时间
                    publish_date = publish_date.replace(tzinfo=timezone.utc)
                
                # 检查是否在24小时内
                if publish_date >= cutoff_time:
                    filtered.append(article)
                else:
                    logger.debug(f"{self.source_name}: 文章超过24小时，已过滤: {article.get('title', '')[:50]}")
                    
            except Exception as e:
                logger.warning(f"{self.source_name}: 日期解析失败，保留文章: {str(e)}")
                # 如果解析失败，保留文章（避免丢失数据）
                filtered.append(article)
        
        return filtered
    
    async def _extract_article_from_json(self, article_item: Dict[str, Any], zipcode: str) -> Optional[Dict[str, Any]]:
        """
        从JSON数据中提取文章信息
        
        Args:
            article_item: JSON中的文章数据
            zipcode: Zipcode
            
        Returns:
            文章数据字典
        """
        try:
            title = article_item.get('title', '')
            if not title:
                return None
            
            # 提取日期
            date_str = article_item.get('date', '')
            if date_str:
                try:
                    # 尝试解析日期格式 "2026-01-26 21:56:00"
                    publish_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").isoformat()
                except Exception as e:
                    logger.debug(f"日期解析失败: {date_str} - {str(e)}")
                    publish_date = self._parse_date(date_str)
            else:
                publish_date = datetime.utcnow().isoformat()
            
            # 提取摘要
            summary = article_item.get('summary', '')
            
            # 提取URL - TODO: 需要验证URL构建逻辑（docid -> URL）
            docid = article_item.get('docid', '')
            if not docid:
                # 如果没有docid，无法构建URL，跳过这篇文章
                logger.warning(f"Newsbreak文章缺少docid，无法构建URL，跳过: {title[:50]}")
                return None
            
            # 尝试从JSON中查找完整URL，如果找不到则使用docid构建临时URL
            # TODO: 验证Newsbreak URL构建逻辑（docid -> URL）
            # 当前使用docid作为临时标识，实际URL可能需要从DOM或其他字段获取
            url = f"https://www.newsbreak.com/news/{docid}"  # 临时URL格式，需要验证
            logger.debug(f"使用docid构建URL: {url} (需要验证)")
            
            return {
                "source": self.source_name,
                "zipcode": zipcode,
                "title": title,
                "url": url,
                "publish_date": publish_date,
                "content": summary or "",
                "content_summary": summary or "",
                "keywords": []
            }
            
        except Exception as e:
            logger.warning(f"从JSON提取文章数据失败: {str(e)}")
            return None
    
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
            # 使用robust mixin提取数据
            article_data = await self.extract_article_data_robust(element, zipcode)
            
            if not article_data:
                return None
            
            # 处理URL（确保是绝对URL）
            url = article_data.get('url', '')
            if url and not url.startswith('http'):
                url = f"https://www.newsbreak.com{url}" if url.startswith('/') else f"https://www.newsbreak.com/{url}"
            
            # 解析日期
            publish_date = article_data.get('publish_date', '')
            if publish_date:
                publish_date = self._parse_date(publish_date)
            else:
                publish_date = datetime.utcnow().isoformat()
            
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
            date_str: 日期字符串（如 "2 hours ago", "Yesterday", "2024-01-15"）
            
        Returns:
            ISO格式日期字符串
        """
        if not date_str:
            return datetime.utcnow().isoformat()
        
        date_str = date_str.strip().lower()
        now = datetime.utcnow()
        
        # 处理相对时间
        if "just now" in date_str or "now" in date_str:
            return now.isoformat()
        elif "minute" in date_str:
            minutes = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 0
            return (now - timedelta(minutes=minutes)).isoformat()
        elif "hour" in date_str:
            hours = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 0
            return (now - timedelta(hours=hours)).isoformat()
        elif "day" in date_str or "yesterday" in date_str:
            days = 1 if "yesterday" in date_str else (int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1)
            return (now - timedelta(days=days)).isoformat()
        elif "week" in date_str:
            weeks = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (now - timedelta(weeks=weeks)).isoformat()
        elif "month" in date_str:
            months = int(re.search(r'(\d+)', date_str).group(1)) if re.search(r'(\d+)', date_str) else 1
            return (now - timedelta(days=months * 30)).isoformat()
        else:
            # 尝试解析标准日期格式
            try:
                from dateutil import parser
                parsed_date = parser.parse(date_str)
                return parsed_date.isoformat()
            except Exception as e:
                logger.debug(f"日期解析失败: {date_str} - {str(e)}")
                return now.isoformat()
