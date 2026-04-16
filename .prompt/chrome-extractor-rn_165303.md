chrome-extractor-rn 的分析不太对吧？ 

1.不是 媒体类型 而应该是输出笔记里面的图片内容嘛 

2.  `title`、`正文`、`评论`、`互动数据` 等全部展开后 不需要你截图然后图片识别啊，这个你直接拿页面元素就可以存在 manifest.json 里面了啊 ； 你要通过 chrome-extractor-rn 来获取具体的html/DOM元素，禁止使用其他手段获取html元素

  3.反而是笔记里面的图片，你需要全部保存下来， 用来分析，因为这个才是必须的   

  就比如 https://www.xiaohongshu.com/explore/69d8c427000000002301fd83?
  app_platform=ios&app_version=9.24&share_from_user_hidden=true&xsec_source=app_share&type=normal&xsec_token=CB-
  nzRARlHwO41zQltAAgse19GYTRBIE3oiu9jt41Y9iA=&author_share=1&xhsshare=WeixinSession&shareRedId=N0kzNEQ2Ok02NzUyOTgwNjY4OTdJRzY9&apptime=1776222010&share_id=ddb45baf17fe4fdc9457a24e0e341061  这个，他的笔记是有两个图片
  的， 