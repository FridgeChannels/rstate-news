# Realtor.com 选择器推荐

基于提供的HTML结构分析

## HTML结构分析

根据提供的HTML元素：
```html
<div class="sc-1ri3r0p-0 hkQVQj">
  <div class="Boxstyles__StyledBox-rui__sc-1p1qqov-0 fJJxfk Cardstyles__StyledCard-rui__sc-42t194-0 cMOpdk">
    <div class="CardMediastyles__StyledCardMedia-rui__sc-1gf45o9-0 jsgzQT card-media">
      ...
    </div>
    <div class="CardContentstyles__StyledCardContent-rui__m7hjnf-0 gQAJGk card-content">
      <a href="/news/real-estate-news/">
        <p class="base__StyledType-rui__sc-18muj27-0 dNmIYP sc-mg9c7m-0 fNtHbR">Real Estate News</p>
      </a>
      <a href="/news/real-estate-news/sarasota-florida-luxury-developement-shellstone-at-waterside/">
        <h3 class="sc-1ewhvwh-0 vgcOr" font-weight="bold">Resort-Style Sarasota Community Comes Equipped With Activities Director and Poolside Grills</h3>
      </a>
      <p class="base__StyledType-rui__sc-18muj27-0 dsOTPE">Luxury living is rising to a new level at a Sarasota, FL, community offering an array of resort-style amenities.</p>
    </div>
  </div>
</div>
```

## 推荐选择器

### 1. 文章容器选择器

**优先级排序：**
1. `div.sc-1ri3r0p-0` - 最外层容器（精确匹配）
2. `div[class*="sc-1ri3r0p-0"]` - 部分匹配（如果类名有变化）
3. `div[class*="Cardstyles"]` - 卡片样式容器
4. `div.card-content` - card-content容器（更通用）

**推荐使用：**
```python
# 主选择器
"div.sc-1ri3r0p-0"

# 备选选择器（按优先级）
[
    "div[class*='sc-1ri3r0p-0']",
    "div[class*='Cardstyles']",
    "div.card-content",
    "div[class*='card']"
]
```

### 2. 标题选择器

**优先级排序：**
1. `h3.sc-1ewhvwh-0` - 精确类名匹配
2. `h3[class*="sc-1ewhvwh-0"]` - 部分匹配
3. `h3[font-weight="bold"]` - 属性匹配
4. `.card-content h3` - 在card-content内的h3

**推荐使用：**
```python
# 主选择器
"h3.sc-1ewhvwh-0"

# 备选选择器
[
    "h3[class*='sc-1ewhvwh-0']",
    "h3[font-weight='bold']",
    ".card-content h3",
    "h3"
]
```

### 3. 链接选择器

**优先级排序：**
1. `a[href*="/news/real-estate-news/"]` - 包含新闻路径的链接（最可靠）
2. `.card-content a[href*="/news/real-estate-news/"]` - 在card-content内
3. `h3 a` - 标题内的链接

**推荐使用：**
```python
# 主选择器（最可靠）
"a[href*='/news/real-estate-news/']"

# 备选选择器
[
    ".card-content a[href*='/news/real-estate-news/']",
    "h3 a",
    "a[href]"
]
```

### 4. 摘要选择器

**优先级排序：**
1. `p.dsOTPE` - 精确类名匹配
2. `p[class*="dsOTPE"]` - 部分匹配
3. `.card-content p` - card-content内的段落（排除标题链接内的p）

**推荐使用：**
```python
# 主选择器
"p.dsOTPE"

# 备选选择器
[
    "p[class*='dsOTPE']",
    ".card-content p:not(a p)",  # card-content内的p，排除链接内的
    ".card-content p"
]
```

### 5. 日期选择器

**注意：** 提供的HTML中没有明显的日期元素，需要在实际页面中查找。

**可能的选择器：**
```python
# 常见日期选择器
[
    "time",
    "time[datetime]",
    ".date",
    ".publish-date",
    "[data-testid*='date']"
]
```

## 实现建议

### 在realtor_scraper.py中的实现

1. **更新文章容器选择器：**
```python
article_selectors = [
    "div.sc-1ri3r0p-0",           # 精确匹配
    "div[class*='sc-1ri3r0p-0']",  # 部分匹配
    "div[class*='Cardstyles']",    # 卡片样式
    "div.card-content",           # 通用
    "div[class*='card']"           # 最通用
]
```

2. **重写extract_article_data_robust方法：**
使用Realtor特定的选择器，优先使用精确匹配，失败后回退到通用选择器。

3. **处理URL：**
确保相对URL转换为绝对URL：`https://www.realtor.com{url}`

## 注意事项

- Realtor.com可能使用动态类名（hash-based），建议同时使用精确匹配和部分匹配
- 类名可能会变化，需要定期验证
- 建议保留通用fallback选择器作为备选
- 摘要选择器需要排除链接内的段落（如"Real Estate News"标签）
