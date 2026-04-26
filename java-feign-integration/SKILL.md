---
name: java-feign-integration
description: "当用户要在 Java 项目中按现有 Feign 模式对接接口时触发，例如“接一个 Feign 接口”“补 decoder”“补 interceptor”。它负责基于项目已有 DTO、decoder、interceptor 和 service 规范补齐接入链路；不用于非 Java 场景、普通代码风格调整或整条链路重构。"
---

# Java Feign Integration

当任务是“对接一个外部接口 / 内部服务接口 / HTTP API”，并且项目使用或适合使用 Feign 时，按下面方式处理。

## 先做的事

- 先在当前项目中搜索 `FeignResponseDecoder`、`FeignDecoder`、`FeignRequestInterceptor`、现有 FeignClient 和相关 DTO。
- 如果项目里已经有相同用途的封装、异常处理、鉴权方式或命名风格，优先沿用，不要另起一套。
- 同步参考 `java-code-style` skill，遵循其中的 DTO、注释、分层、校验、`Result` 返回等规范。

## 实现顺序

1. 先定义或补齐 request DTO 和 response DTO。
2. 再声明 Feign 接口，方法签名直接使用 DTO，禁止直接裸传 `Map`、`JSONObject`、`Object`，除非项目现有约定就是如此。
3. 返回解码有统一格式时，优先参考已有 `FeignResponseDecoder` 实现或补齐 `FeignDecoder`，保持异常处理和结果解析方式一致。
4. 需要统一鉴权、token、签名、traceId 或公共 header 时，再参考 `FeignRequestInterceptor` 实现或补齐 Interceptor。
5. Feign 层只负责接口声明和基础配置，业务编排、参数组装、结果转换放在 service。

## Demo

生成结构参考如Demo所示， 如果代码结构能够复用以下代码，则
```
FeignConfiguration
FeignLogger
FeignRequestInterceptor
FeignResponseDecoder
```

否则 参考以上代码，补齐 `FeignConfiguration`/`FeignLogger`/`FeignRequestInterceptor`/`FeignResponseDecoder`

Demo：
```
@FeignClient(
	name = "RestImmsgService",
	url = "${immsg.baseUrl}",                    // 配置文件里定义 baseUrl
	configuration = {
		FeignConfiguration.class,
		ImmsgRequestInterceptor.class,
		ImmsgResponseDecoder.class
	}
)
```

## 强约束

- Feign 入参和出参都使用 DTO。
- 不要把业务逻辑写进 Feign 接口、Decoder 或 Interceptor。
- 不要为了“优雅”重构整条链路，优先最小必要改动。
- 如果项目里已有可复用的 decoder / interceptor / config，优先在原有基础上补代码，不重复造轮子。
- 生成代码时，优先兼容项目现有注解、包结构、命名和异常体系。

## 代码生成偏好

- request DTO 字段补齐 `@Schema` 和必要的校验注解。
- request DTO 要使用 `@JsonInclude(JsonInclude.Include.NON_NULL)` 注解，避免传入 `null` 值
- response DTO 字段语义要明确，避免直接返回原始嵌套 `Map`。
- DTO 只包含要传给远程的字段和数据
- FeignClient 方法名按业务语义命名，不写成无意义的 `invoke`、`call`。
- service 中补充必要注释，重点说明参数转换、异常分支和接口结果判定。
- 如果对方接口返回是通用包裹结构，Decoder 负责统一拆包；service 不要重复写同样的拆包逻辑。
- FeignClient 接口禁止返回 void
- FeignClient url 使用 `${xxx}` 代替硬编码

## 默认工作流

1. 搜索项目内已有 Feign 相关实现和相似接口接入方式。
2. 按 `java-code-style` 规范补 DTO。
3. 生成或补齐 FeignClient。
4. 按需补 `FeignDecoder` / `FeignRequestInterceptor`。
5. 在 service 中完成业务调用链，controller 仅负责收参与返回。
