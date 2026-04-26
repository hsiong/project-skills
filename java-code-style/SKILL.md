---
name: java-code-style
description: "当用户要生成、补全、修改或评审 Java 后端代码时触发。它按现有项目风格产出最小改动的 Java 代码；不用于前端、运维或与 Java 无关的任务。"
---

# Java Code Style

按下面规则生成 Java 代码，并优先兼容用户当前项目已有风格；如果项目现有写法与本 skill 不冲突，保持一致。

## 核心规范

- 尽量避免重复代码，但不要为了“一两行重复代码”强行拆出额外私有方法、工具类或抽象层
- 多个代码块有复用代码的，抽离为工具类或私有方法，避免重复代码
- 如果没有复用代码，直接保留在一个完整的大方法中，优先保证调用链直观
- 新增代码时优先做最小必要改动，不顺手扩展范围，不主动重构整条链路
- 除非用户明确要求，直接修改相关代码即可

## 注释

- 为所有方法补充 JavaDoc。
- 有入参时使用 `@param` 描述参数含义。
- 有返回值时使用 `@return` 描述返回结果。
- `void` 方法不要硬写 `@return`。
- 注释直接说明业务目的和入参与返回关系，不写空泛表述。
- 生成注释时，优先解释“为什么这样处理”，不是重复代码字面意思。
- 关键代码必须加注释，重点解释业务判断、分支原因、边界处理和数据转换，不写无意义的逐行注释。


示例：

```java
/**
 * 根据用户ID查询有效订单信息。
 *
 * @param userId 用户ID
 * @param includeClosed 是否包含已关闭订单
 * @return 当前用户可见的订单列表
 */
public List<OrderVO> queryValidOrders(Long userId, boolean includeClosed) {
    // 先查询原始订单数据，后续统一做状态过滤
    List<Order> orders = orderMapper.selectByUserId(userId);
    if (!includeClosed) {
        orders = orders.stream()
                .filter(order -> !Objects.equals(order.getStatus(), OrderStatus.CLOSED))
                .toList();
    }
    return buildOrderVOList(orders);
}
```

## 分层约束

- 接口层或 controller 层只负责接收参数、调用 service、返回结果。
- 具体业务逻辑、业务判断、数据编排、状态处理放在 service 或 service impl 中。
- 不是数据库 CRUD 的代码，无需使用 service impl，直接用 class service 即可。
- 只有在项目本身明确存在数据库 CRUD 分层约定，或者用户明确要求时，才补 service impl。
- 不要把核心业务逻辑直接写在 controller、feign 接口、RPC 接口定义或 API 声明层。
- 如果同时生成 controller 和 service，先保证接口签名清晰，再把完整逻辑落到 service。

## 实体与请求对象

- DTO、Entity、Pojo、VO 等实体类字段需要使用 `@Schema` 描述字段含义。
- 实体类本身优先使用 `@Data`。
- request DTO 中必填字段使用 `@NotBlank` 或 `@NotNull`。
- 必填校验注解必须补充 `message`，格式优先使用“xxx不能为空”。
- 字符串类型必填优先使用 `@NotBlank`；非字符串对象、数字或集合是否为空校验按类型选择 `@NotNull`。
- DTO 不要使用内部类
- 生成 request DTO 时，同步补齐 `@Schema`、必填校验注解和 `message`。

示例：

```java
@Data
@Schema(description = "创建订单请求")
public class CreateOrderRequestDTO {

    @Schema(description = "用户ID")
    @NotNull(message = "用户ID不能为空")
    private Long userId;

    @Schema(description = "订单标题")
    @NotBlank(message = "订单标题不能为空")
    private String title;
}
```

## 配置项约束

- 禁止访问任何 `application-*.yml` 文件，但可以访问 `application.yml`
- 注意，代码中使用的配置项要与 `application.yml` 配置一致, 如 `${xxx}`, `@ConfigurationProperties` 等
- 如需新增配置项，默认把配置项加入 `application.yml`, 并引用 `${config.xxx.xxx}`
- 新增的`${config.xxx}`无需写在配置文件里，直接在 terminal 日志中打印新增 key 和建议值。
- 打印时优先给出可直接复制的配置片段，保持 key 层级完整。
- 使用 `xxxProperties` 命名

## 测试代码约定

- 测试类如需调用 api 接口, 请基于 `ynfy-tool-httpconnect` 实现
- 如果用户要求生成测试方法，实现逻辑必须非常简单，方便直接运行和理解。
- 测试优先覆盖主流程、关键分支和明显边界，不写过度复杂的构造逻辑。
- 除非用户要求, 无需你自动测试，我自行手动测试即可

## Controller 约束

- Controller 方法使用 `@Operation` 描述接口用途。
- 优先使用 Post 请求，除非用户明确要求或场景天然更适合 Get。
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

## sql
+ 如涉及到表操作, 请将 sql 保存到 file/sql 目录下, sql 文件命名为 `{ddyyhhmmss}.sql`
+ 如果表已经存在, 请不要直接改动建表语句, 而是使用 'alter table' 命令

## 生成代码时的执行方式

- 生成 service 方法时，把主要逻辑写完整，不要只留“TODO”或空壳实现。
- 使用框架内已有的日志工具，在关键节点 加入 日志打印
- 缩进使用 tab
- keep indents on empty lines
- Avoid passing complex expressions, chained calls, or request getters directly into method parameters. Extract method inputs into clearly named local variables first, then pass those variables to the method. This makes the business meaning of each parameter explicit, improves readability, and makes future validation, logging, debugging, and null checks easier.
  ```
  String profileId = request.getProfileId();
  CustomerDingTalkRobotDTO customerInfo =
        restCustomDataService.getDingTalkRobotCustomer(profileId);
  # Instead of:
  # CustomerDingTalkRobotDTO customerInfo = restCustomDataService.getDingTalkRobotCustomer(request.getProfileId());
  ```



