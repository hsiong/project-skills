chrome-extractor-rn-v2 完全不对  你要保存我chrome-extractor-rn 展开评论的这些全部逻辑啊    你给我全删了干嘛？
   只要你把截图这块的逻辑改为借助大模型来获取`title`、`正文`、`评论`、`互动数据`以及图片和视频（注意，是通过大模型获取，而不是写死的dom）；然后把解析后的`title`、`正文`、`评论`、`互动数据`存到
   manifest.json，互动数据的格式是

   - Split `互动数据` by conversation block with fenced code blocks, for example:

```text
- xxx
- xx
```

```text
- xxx
- xx
```

最后由大模型图片识别图片， 并整合 manifest.json；最后生成 REPORT.md
