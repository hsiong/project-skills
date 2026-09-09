---
name: code-backend-python-style
description: "当用户要生成、补全、修改或评审 Python 代码时触发。它按现有项目风格做最小必要改动；不用于前端、纯运维或需要大规模重构的任务。"
---

# Python Code Style
必须按下面规则生成 Python 代码, 不能遗漏； 必须满足 skill `code-backend-common` 中的约定

## FastAPI 与接口代码
- 框架使用 `fastapi`
- 路由层只负责接收参数、调用 service 或核心逻辑、返回结果。api中禁止写任何方法实现, 新增接口保持函数命名清晰，参数和返回结构稳定
- 具体业务判断、数据拼装、状态处理放在业务方法中。
- 请求体、响应体满足 实体与请求对象 约束。

## SQL 与 ORM
+ SQL 数据库默认使用 postgres, 参考 `postgres_init.py`
+ ORM 使用 `SQLAlchemy`
+ ORM Entity crud 链路存到 `model` 目录下, `model/repo, entity, service/xxx`
+ Entity model 需要兼容 `SQLAlchemy` 模型定义
+ `SQLAlchemy` 模型定义完全兼容 `pydantic`模型吗? 如果不兼容,  完成 `pydantic` 和 `SQLAlchemy` 模型互转方法
  + 如果读取的 `POSTGRES_URL` 为空, 则不 import SQLAlchemy 相关类, 避免报错 因为很多项目无需 SQLAlchemy
+ `repo` 只负责实现最基础的 `add update delete list`, `service` 负责业务逻辑
- 无需表结构检查, 表结构检查写在 `create_app` 中
- crud 需要使用 `postgres_session`, 禁止使用 engine

## 方法
- 同一批业务只能放到 `core` 同一个文件内, API 路由只从一个 core 文件导入方法
- Avoid passing complex expressions, chained calls, or request getters directly into method parameters. Extract method inputs into clearly named local variables first, then pass those variables to the method. This makes the business meaning of each parameter explicit, improves readability, and makes future validation, logging, debugging, and null checks easier.
- 禁止使用 `async`/`await`
- 如需 main 实现的, 不用单独写main()  而是直接写在if __name__ == "__main__":

## 包与模块
项目按服务划分为不同的顶层 package，例如 `etf_assistant`。
每个服务 package 内部包含该服务独立需要的配置、模型、API、业务服务、定时任务等模块，例如：
```
etf_assistant/
  config/
  model/
  api/
  services/
  schedules/
  ...
```
在每个模块内部，再根据具体业务场景或功能边界拆分为不同的 Python 文件。例如 `etf_assistant`、`user_assistant`、`trade_assistant`。

## 实体与请求对象
- 基于 `pydantic` 模型定义
- 接口使用以下解析 `request_dict: BotAnalyseApiRequest = BotAnalyseApiRequest.model_validate(request_json)`
- 应按“对象类型 + 同一业务”聚合，而不是“一类一个文件”; 命名按照 `xxentity`、`xxdto`、`xxreq`、`xxvo` 的命名规则: model/entity, model/dto, model/req, model/vo
- 禁止使用 `Dict`, 而是使用对象

## 依赖
- 依赖需要加入版本
- 依赖文件中如果缺乏 `-i https://pypi.tuna.tsinghua.edu.cn/simple`, 自动补充
- 禁止自动修改依赖文件名称
- 该项目下的所有项目，执行测试时，应使用项目依赖，禁止使用全局 pip 污染全局依赖；没有项目环境时 使用临时环境 `/tmp/项目名/bin/python`，但是临时环境结束后要移除

## 配置项约束
- 新增的配置项，放到 `config/settings.py` 中, 比如 `POSTGRES_URL = env.get("POSTGRES_URL")`, 不需要默认值；新增的具体配置, 直接在 terminal 日志中打印新增 key 和建议值, 比如 `POSTGRES_URL=xxx`
- 如需使用常量, 放到 `constant` 文件夹下合适的类中