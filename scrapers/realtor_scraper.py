"""
Realtor.com采集器
采集房地产行业新闻
"""
import asyncio
import re
import random
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from scrapers.real_estate_scraper import RealEstateScraper
from scrapers.robust_scraper_mixin import RobustScraperMixin
from utils.logger import logger
from config.settings import settings


class RealtorScraper(RealEstateScraper, RobustScraperMixin):
    """Realtor.com新闻采集器"""
    
    # TODO: 需要重新保存DOM并分析Realtor.com结构
    # 当前DOM文件可能未保存成功，需要运行 save_all_doms.py 重新保存并分析
    
    def __init__(self, headless: bool = False):
        """
        初始化Realtor.com采集器
        
        Args:
            headless: 是否使用headless模式（默认False，用于验证反爬虫问题）
        """
        super().__init__("Realtor.com", "https://www.realtor.com/news/real-estate-news/")
        self.use_headless = headless  # Realtor.com使用headed模式验证
    
    async def _scrape_real_estate_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        采集Realtor.com的房地产新闻
        
        Args:
            limit: 采集数量限制
            
        Returns:
            文章列表
        """
        articles = []
        page = None
        
        try:
            # Realtor.com使用headed模式验证反爬虫问题
            await self._setup_browser(headless=self.use_headless)
            # Realtor.com 在 macOS 上使用 persistent context（复用 cookie）时，必须全程复用同一个 context，
            # 否则会在 _create_page() 内部走到默认 headless=True 分支，导致“又被封/又被关页”。
            if (not self.use_headless) and sys.platform == "darwin" and getattr(self, "_is_persistent_context", False) and self.context:
                self.context.on("dialog", lambda dialog: dialog.accept())
                page = await self.context.new_page()
            else:
                page = await self._create_page()
            
            # 为Realtor.com添加增强的反检测脚本
            await page.add_init_script("""
                // 隐藏webdriver标志
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // 添加真实的Chrome对象
                window.chrome = {
                    runtime: {}
                };
                
                // 覆盖plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // 覆盖languages
                Object.defineProperty(navigator, 'languages', {
                    // 与 en-US 画像保持一致
                    get: () => ['en-US', 'en']
                });
                
                // 覆盖permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            logger.debug(f"访问: {self.base_url}")
            
            # 使用重试机制访问页面
            # 注意：_retry_with_backoff 的第二个位置参数是 max_retries，不能把 url 作为位置参数传进去
            # 节奏控制：避免短时间多次导航触发风控
            await asyncio.sleep(settings.realtor_min_request_interval_seconds)
            await self._retry_with_backoff(
                page.goto,
                3,          # max_retries
                1.0,        # base_delay
                self.base_url,
                wait_until="domcontentloaded",  # 改为domcontentloaded，避免networkidle触发检测
                timeout=30000
            )
            
            # 等待页面DOM加载完成
            await asyncio.sleep(2)  # 固定延迟，让页面开始渲染

            # 首次人工放行模式：给用户时间在弹出窗口中完成验证/放行
            if (not self.use_headless) and settings.realtor_manual_gate_seconds > 0:
                logger.info(
                    f"Realtor.com: 手动放行窗口已打开，请在 {settings.realtor_manual_gate_seconds}s 内完成验证/放行（若无需操作可将 REALTOR_MANUAL_GATE_SECONDS=0）"
                )
                await asyncio.sleep(settings.realtor_manual_gate_seconds)

            # 封禁页“过渡等待”：Realtor 有时先返回封禁/等待页，约 2s 后由前端替换为正常内容，
            # 在此时间内不判定为封禁，避免误杀。
            settlement = getattr(settings, "realtor_block_settlement_seconds", 4.0)
            if settlement > 0:
                logger.debug(f"Realtor.com: 等待封禁页过渡 {settlement}s 后再检测")
                await asyncio.sleep(settlement)

            # 快速判定是否命中封禁页（用于日志一眼识别）
            # try:
            #     body_text = await page.locator("body").inner_text(timeout=5000)
            #     block_keywords = [
            #         "Your request could not be processed",
            #         "unblockrequest@realtor.com",
            #     ]
            #     hit = next((kw for kw in block_keywords if kw in body_text), None)
            #     if hit:
            #         logger.error(f"REALTOR_BLOCK_PAGE_DETECTED: keyword={hit}")
            #         # 命中封禁：保存截图 + HTML，并直接终止本次抓取（避免反复触发加重封禁）
            #         await self._dump_block_artifacts(page, reason=hit)
            #         return []
            # except Exception as e:
            #     logger.debug(f"封禁页快速检测失败（可忽略）: {str(e)}")
            
            # 处理可能的弹窗和Cloudflare验证
            try:
                # 关闭可能的弹窗
                close_selectors = [
                    "button[aria-label*='close' i]",
                    "button[aria-label*='Close' i]",
                    ".close-button",
                    "[data-testid='close']",
                    ".modal-close",
                    ".cookie-consent button"
                ]
                for selector in close_selectors:
                    try:
                        btn = await page.query_selector(selector)
                        if btn and await btn.is_visible():
                            await btn.click(timeout=2000)
                            await asyncio.sleep(1)
                            logger.debug(f"关闭弹窗: {selector}")
                            break
                    except:
                        continue
                
                # 检查是否有Cloudflare挑战
                cf_challenge = await page.query_selector("#challenge-form, .cf-browser-verification")
                if cf_challenge:
                    logger.warning("检测到Cloudflare验证，等待自动处理...")
                    await asyncio.sleep(10)  # 增加等待时间
            except Exception as e:
                logger.debug(f"检查弹窗/Cloudflare验证失败: {str(e)}")
            
            # 添加行为模拟：随机滚动
            try:
                # 分段滚动 + 随机停留（轻量拟真）
                await page.evaluate("window.scrollTo(0, 200)")
                await asyncio.sleep(random.uniform(0.8, 1.6))
                await page.evaluate("window.scrollTo(0, 600)")
                await asyncio.sleep(random.uniform(0.8, 1.8))
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(random.uniform(0.6, 1.4))
            except Exception as e:
                logger.debug(f"滚动模拟失败: {str(e)}")
            
            # 等待文章列表加载 - 使用实际DOM结构的选择器
            article_selectors = [
                "div.sc-1ri3r0p-0",  # 根据实际HTML结构
                "div[class*='sc-1ri3r0p-0']",  # 部分匹配
                "div[class*='Cardstyles']",  # 卡片样式
                "div.card-content",  # 通用
                "div[class*='card']",  # 最通用
                "article",
                ".article-card",
                ".news-item"
            ]
            
            # 等待文章元素出现（使用实际选择器）
            article_found = False
            for selector in article_selectors[:3]:  # 优先使用前3个实际选择器
                try:
                    await page.wait_for_selector(selector, timeout=10000)
                    logger.debug(f"找到文章容器: {selector}")
                    article_found = True
                    break
                except Exception as e:
                    logger.debug(f"等待选择器 {selector} 超时: {str(e)}")
                    continue
            
            if not article_found:
                logger.warning("未找到文章容器，继续尝试通用选择器...")
                await asyncio.sleep(3)  # 额外等待
            
            # 在headed模式下保存截图（用于验证）
            if not self.use_headless:
                try:
                    from pathlib import Path
                    screenshot_dir = Path("logs/realtor_screenshots")
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    screenshot_path = screenshot_dir / f"realtor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"截图已保存: {screenshot_path}")
                except Exception as e:
                    logger.debug(f"保存截图失败: {str(e)}")
            
            # 使用robust方法查找元素
            article_elements = await self.find_elements_with_fallback(page, article_selectors)
            
            logger.debug(f"找到 {len(article_elements)} 个文章元素")
            
            for i, element in enumerate(article_elements[:limit]):
                try:
                    article = await self._extract_article_data(element)
                    if article:
                        articles.append(article)
                        await self._random_delay(0.5, 1.5)
                except Exception as e:
                    logger.warning(f"提取第 {i+1} 篇文章失败: {str(e)}", exc_info=True)
                    continue
            
        except Exception as e:
            logger.error(f"Realtor.com采集过程出错: {str(e)}", exc_info=True)
        finally:
            # 确保页面和浏览器资源都被清理
            # 注意：不需要单独关闭page，cleanup()会关闭整个context（包括所有页面）
            await self.cleanup()
        
        return articles

    async def _dump_block_artifacts(self, page, reason: str) -> None:
        """
        命中封禁页时保存证据，便于排查：
        - 截图：logs/realtor_blocked/
        - HTML：logs/realtor_blocked/
        """
        try:
            from pathlib import Path
            blocked_dir = Path("logs/realtor_blocked")
            blocked_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_reason = re.sub(r"[^a-zA-Z0-9_-]+", "_", reason)[:40]

            screenshot_path = blocked_dir / f"blocked_{ts}_{safe_reason}.png"
            html_path = blocked_dir / f"blocked_{ts}_{safe_reason}.html"

            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Realtor.com: 封禁页截图已保存: {screenshot_path}")
            except Exception as e:
                logger.debug(f"Realtor.com: 封禁页截图保存失败: {str(e)}")

            try:
                html = await page.content()
                html_path.write_text(html, encoding="utf-8")
                logger.info(f"Realtor.com: 封禁页HTML已保存: {html_path}")
            except Exception as e:
                logger.debug(f"Realtor.com: 封禁页HTML保存失败: {str(e)}")
        except Exception as e:
            logger.debug(f"Realtor.com: dump封禁证据失败: {str(e)}")
    
    async def extract_article_data_robust(
        self,
        element,
        zipcode: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用Realtor.com特定的选择器提取文章数据
        优先使用实际DOM结构的选择器，失败后回退到通用fallback
        """
        try:
            # 标题 - 使用Realtor特定选择器
            title = await self.find_element_with_fallback(
                element,
                [
                    "h3.sc-1ewhvwh-0",  # 精确匹配
                    "h3[class*='sc-1ewhvwh-0']",  # 部分匹配
                    "h3[font-weight='bold']",  # 属性匹配
                    ".card-content h3",  # card-content内的h3
                    "h3",  # 通用fallback
                    "h2", "h1"
                ]
            )
            
            # 链接 - 使用Realtor特定选择器
            link_elem = await self.find_element_with_fallback(
                element,
                [
                    "a[href*='/news/real-estate-news/']",  # 最可靠
                    ".card-content a[href*='/news/real-estate-news/']",  # card-content内
                    "h3 a",  # 标题内的链接
                    "a[href]",  # 通用链接
                ],
                extract_text=False
            )
            
            url = ""
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    url = href
            
            # 摘要 - 使用Realtor特定选择器
            summary = await self.find_element_with_fallback(
                element,
                [
                    "p.dsOTPE",  # 精确匹配
                    "p[class*='dsOTPE']",  # 部分匹配
                    ".card-content p:not(a p)",  # card-content内的p，排除链接内的
                    ".card-content p",  # card-content内的p
                    "p"  # 通用fallback
                ]
            )
            
            # 日期 - 尝试多种选择器
            date_elem = await self.find_element_with_fallback(
                element,
                [
                    "time[datetime]",
                    "time",
                    ".date", ".publish-date", ".published-date",
                    "[datetime]",
                    ".timestamp"
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
            
            # 验证必需字段
            if not title or not url:
                # 如果特定选择器失败，回退到通用方法
                logger.debug("Realtor特定选择器失败，回退到通用fallback")
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
            logger.warning(f"Realtor特定选择器提取失败: {str(e)}，回退到通用方法")
            return await super().extract_article_data_robust(element, zipcode)
    
    async def _extract_article_data(self, element) -> Dict[str, Any]:
        """从文章元素中提取数据（使用Realtor特定的选择器）"""
        try:
            # 使用Realtor特定的robust方法提取数据
            article_data = await self.extract_article_data_robust(element)
            
            if not article_data:
                return None
            
            # 处理URL
            url = article_data.get('url', '')
            if url and not url.startswith('http'):
                url = f"https://www.realtor.com{url}" if url.startswith('/') else f"https://www.realtor.com/{url}"
            
            # 解析日期
            publish_date = article_data.get('publish_date', '')
            if publish_date:
                publish_date = self._parse_date(publish_date)
            else:
                publish_date = datetime.utcnow().isoformat()
            
            return {
                "source": self.source_name,
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
        """解析日期字符串为ISO格式"""
        if not date_str:
            return datetime.utcnow().isoformat()
        
        try:
            from dateutil import parser
            parsed_date = parser.parse(date_str)
            return parsed_date.isoformat()
        except Exception as e:
            logger.debug(f"日期解析失败: {date_str} - {str(e)}")
            return datetime.utcnow().isoformat()
