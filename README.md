# MinewaysMobile-Resources

Mineways Mobile 的官方资源目录。App 只读取本仓库根目录的多份 JSON；资源二进制放 GitHub Releases。

## 文件

```text
catalog.json      总清单：版本 + 每个文件的 sha256
items.json        资源条目
creators.json     创作者
collections.json  主题合集 / 官方创作者合集
featured.json     本周精选
rankings.json     排行榜
search.json       别名 / 同义词 / 热门词
```

## 发布

1. 修改对应 JSON
2. 更新 `catalog.json` 的 `catalog_version` / `updated_at`
3. 运行 `python tools/build_catalog.py`
4. 运行 `python tools/validate_resources.py`
5. 提交 PR

官方资源必须每个资源一个独立 Release，tag 形如 `res-map-skyblock-v1.0`，不可覆盖旧资产。

## 许可

目录只承载元数据；资源版权归各创作者。没有明确分发授权的资源不会收录。
