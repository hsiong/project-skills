---
name: code-backend-java-style
description: "当用户要生成、补全、修改或评审 Java 后端代码时触发。它按现有项目风格产出最小改动的 Java 代码；不用于前端、运维或与 Java 无关的任务。"
---

# Java Code Style
必须按下面规则生成 Java 代码, 不能遗漏； 必须满足 skill `code-backend-common` 中的约定

## 测试代码约定
- 测试类如需调用 api 接口, 请基于 `ynfy-tool-httpconnect` 实现
- 输出 excel, 请基于 `EasyExcel`
- 测试的相关类也要符合 `## 实体与请求对象` 的约定

## 注释
- 为所有方法补充 JavaDoc。
- 有入参时使用 `@param` 描述参数含义。
- 有返回值时使用 `@return` 描述返回结果。
- `void` 方法不要硬写 `@return`。
示例：
```java
/**
 * 根据用户ID查询有效订单信息。
 *
 * @param userId 用户ID
 */
public List<OrderVO> queryValidOrders(Long userId) {
    // 先查询原始订单数据，后续统一做状态过滤
    return orderMapper.selectByUserId(userId);
}
```

## 分层约束
- 接口层或 controller 层只负责接收参数、调用 service、返回结果。
- 具体业务逻辑、业务判断、数据编排、状态处理放在 service 或 service impl 中。
- 不是数据库 CRUD 的代码，无需使用 service impl，直接用 class service 即可。
- 只有在项目本身明确存在数据库 CRUD 分层约定，或者用户明确要求时，才补 service impl。
- 不要把核心业务逻辑直接写在 controller、feign 接口、RPC 接口定义或 API 声明层。
- 如果同时生成 controller 和 service，先保证接口签名清晰，再把完整逻辑落到 service。

## Controller 约束

- Controller 方法使用 `@Operation` 描述接口用途。
- 默认优先使用 Post 请求，除非场景天然更适合 Get。
- 查询接口方法名以 `getXXX` 形式命名。
- Controller 返回统一使用 `Result` 类。
- Controller 内部只做收参、基础校验、调用 service、封装 `Result`，不要下沉业务实现。
- 生成 controller 时，只保留参数接收、基础校验、调用 service、封装返回。
- 生成接口定义时，保证命名、入参、返回值和实现类保持一致。
- 生成 controller 时，同步检查是否满足 `@Operation`、Post 优先、查询接口 `getXXX`、`Result` 返回这几项约束。
示例：
```java
@PostMapping("/getOrderDetail")
@Operation(summary = "查询订单详情")
public Result<OrderDetailVO> getOrderDetail(@Validated @RequestBody OrderDetailRequestDTO requestDTO) {
    return Result.success(orderService.getOrderDetail(requestDTO));
}
```

## Service
- 生成 service 方法时，把主要逻辑写完整，不要只留“TODO”或空壳实现。
- 同一类的代码, 名称前缀应相同, 比如 `XXXCallbackService` 命名不便管理   应该命名 `CallbackXXXService`  这样都在一起

## 实体与请求对象
- DTO、Entity、Pojo、VO 等实体类字段需要使用 `@Schema` 描述字段含义。
- 实体类本身优先使用 `@Data`。
- request DTO 中必填字段使用 `@NotBlank` 或 `@NotNull`。
- 必填校验注解必须补充 `message`，格式优先使用“xxx不能为空”。
- 字符串类型必填优先使用 `@NotBlank`；非字符串对象、数字或集合是否为空校验按类型选择 `@NotNull`。
- 生成 request DTO 时，同步补齐 `@Schema`、必填校验注解和 `message`。
- 使用了`@NotBlank`就无需再使用`@JsonSetter(nulls = Nulls.SKIP)`
- 驼峰命名接口无需使用 `@JsonProperty` 除非是必须传入或接收 下划线命名字段
- 上下文拆成独立类
- 不要全参数赋值, 先new再set, 避免连续类型赋值异常
- 禁止使用 `@TableField(exist = false)` , 而是应该使用单独的 DTO 或 VO
示例：
```java
@Data
@Schema(description = "创建订单请求")
public class CreateOrderRequestDTO {
    @Schema(description = "用户ID")
    @NotNull(message = "用户ID不能为空")
    private Long userId;
}
```
+ 日期入参使用注解
```
	@DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
	@JSONField(format = "yyyy-MM-dd HH:mm:ss")
	@JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
```
+ 实体与请求对象与DTO 字段禁止使用初始值

### DTO 拆分类与包路径规则
DTO 禁止使用内部类。原本作为内部类存在的 DTO，必须按业务层级拆成独立 public class，并放入与父级 DTO 对应的子包中。 拆分规则：
1. 顶层 DTO 放在当前业务 DTO 包下，例如： dto.dingtalkmessagedto.TextDTO
2. 原本属于某个 DTO 内部结构的子 DTO，放到以父 DTO 小写名称命名的子包下，例如：TextDTO 内部的 ReplyDTO 放到： dto.dingtalkmessagedto.textdto.ReplyDTO
3. 如果子 DTO 下面还有更深层结构，继续按父级 DTO 小写名称递归建包，例如： ReplyDTO 内部的 ReplyTextDTO 放到： dto.dingtalkmessagedto.textdto.replydto.ReplyTextDTO
4. 包名使用小写，类名保持 PascalCase，并保留 DTO 后缀。
5. 拆分后，父 DTO 通过字段引用子 DTO 类型，不再声明 static class / inner class。

## enum
- 使用到枚举的, 实体直接保存枚举, 枚举参考以下实现
```
@Getter
@AllArgsConstructor
public enum xxxEnum {
	xxx("code", "name");

	@EnumValue
	@JsonValue
	private final String code;
	private final String name;

	@JsonCreator
	public static xxxEnum of(Object code) {
		xxx
	}
}
```

## 方法
- Avoid passing complex expressions, chained calls, or request getters directly into method parameters. Extract method inputs into clearly named local variables first, then pass those variables to the method. This makes the business meaning of each parameter explicit, improves readability, and makes future validation, logging, debugging, and null checks easier. 禁止使用 redundant  Local variable
  ```
  String profileId = request.getProfileId();
  CustomerDingTalkRobotDTO customerInfo =
        restCustomDataService.getDingTalkRobotCustomer(profileId);
  # Instead of:
  # CustomerDingTalkRobotDTO customerInfo = restCustomDataService.getDingTalkRobotCustomer(request.getProfileId());
  ```
- 下载接口不要返回 FileSystemResource 让框架自己处理资源流
- service 方法入参一般使用 dto 传参, 如果是复用代码, 可以直接传入变量作为参数, 就不用非要dto了

## 其他
- 提到缓存, 请使用 `@Cacheable`; 同时要有明确方法实现同一cache的`@CacheEvict`
- 默认不存储 `null` 值, 使用 `unless = "#result == null"`
- 使用 `@Async` 实现多线程/异步，不要使用 `Executors`
- 每个多线程/异步方法使用单独的名称, 不用共用线程池; 每个多线程/异步方法使用独立的类

## 核心规范
- 禁止访问任何 `application-*.yml` 文件，但可以访问 `application.yml`
- 注意，代码中使用的配置项要与 `application.yml` 配置一致, 如 `${xxx}`, `@ConfigurationProperties` 等； 新增DTO使用 `xxxProperties` 命名
- 如需新增配置项，把配置项加入 `application.yml`, 并引用 `${config.xxx.xxx}`, 新增的`${config.xxx}`无需写在配置文件里，直接在 terminal 日志中打印新增 key 和建议值。 打印时优先给出可直接复制的配置片段，保持 key 层级完整。
- 禁止使用形如以下更新代码  这会导致数据全部丢失 ! 
 ```
						xxx updateEntity = new xxx();
						updateEntity.setId(recordId);
						...
						xxxMapper.updateById(updateEntity);
 ```