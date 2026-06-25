---
name: java-spring-workflow
description: Use when working in Java or Spring Boot codebases for any task involving feature development, debugging, refactoring, schema changes, dependency management, testing, or security. Covers Maven single/multi-module projects, Spring Boot 3.x, MyBatis-Plus, Spring Security 6, JUnit 5, and Testcontainers. Prefer this over ad hoc Java reasoning to stay on correct Spring Boot 3 patterns and avoid Spring Boot 2 regressions.
---

# Java Spring Workflow

这是 Java / Spring Boot 开发的标准工作流。适用于 Spring Boot 3.x + Maven/Gradle 项目（单模块或多模块）。所有规范默认基于 Spring Boot 3.x / Java 17+；如仓库使用旧版本，先确认版本再应用规则。

棕地仓库做结构追踪、调用链分析时，配合 `serena-workflow` 使用。

---

## 1. 开始前：定位项目结构

在写任何代码之前，先读懂项目形状。

```bash
# 判断构建工具和项目类型
ls pom.xml build.gradle build.gradle.kts    # Maven or Gradle
ls */pom.xml                                 # 多模块子模块（Maven）
ls */build.gradle.kts                        # 多模块子模块（Gradle）
awk '/<modules>/{flag=1} flag{print} /<\/modules>/{flag=0}' pom.xml  # Maven 模块列表
grep -n -A5 "<parent>" pom.xml      # Spring Boot 父 POM 版本
grep "springBootVersion\|id.*spring-boot" build.gradle.kts 2>/dev/null  # Gradle SB 版本
```

**Gradle 等效命令**（如仓库用 Gradle，用以下替代 Maven 命令）：

```bash
./gradlew build -x test          # 全量构建跳过测试
./gradlew test                   # 全部单元测试
./gradlew integrationTest        # 集成测试（需项目配置对应 task）
./gradlew dependencies           # 查看依赖树
./gradlew bootBuildImage         # OCI 镜像
```

多模块项目必须分清各模块职责：
- **api / web**：Controller、DTO、全局异常、Swagger 配置
- **service / application**：业务逻辑、事务、状态机
- **domain**：Entity、枚举、Repository 接口
- **infra / dal**：Mapper、Redis、消息、外部调用
- **common**：工具类、统一响应体、常量、自定义注解

如果仓库没有明显分层，**不要自行重组结构**，先在 AGENTS.md 或 memory 中记录当前实际分层，再提方案。

---

## 2. Maven 命令速查

```bash
# 全量构建（跳过测试）
mvn clean package -DskipTests

# 多模块：只构建指定模块及其依赖
mvn package -pl moving-api -am -DskipTests

# 离线构建（CI/容器内依赖已缓存）
mvn package -o -DskipTests

# 运行测试
mvn test                            # 全部单元测试
mvn test -Dgroups=unit              # 按 JUnit 5 Tag 过滤
mvn verify -Dgroups=integration     # 集成测试（含 Testcontainers）

# 查看依赖树（排查冲突）
mvn dependency:tree -Dincludes=groupId:artifactId

# 查看传递依赖引入路径
mvn dependency:tree | grep "conflict"

# 更新父 pom 版本
mvn versions:update-parent

# 生成 Spring Boot OCI 镜像
mvn spring-boot:build-image         # buildpacks（不需要 Dockerfile）
```

---

## 3. Spring Boot 3.x 关键变化（避免 Boot 2 回归）

这是最高频出错的地方，每次写 Spring Boot 代码前先对照：

| 旧写法（Boot 2）| 正确写法（Boot 3） |
|---|---|
| `extends WebSecurityConfigurerAdapter` | 删除继承，注册 `SecurityFilterChain` Bean |
| `javax.persistence.*` | `jakarta.persistence.*` |
| `javax.validation.*` | `jakarta.validation.*` |
| `javax.servlet.*` | `jakarta.servlet.*` |
| `spring.redis.*` 配置键 | `spring.data.redis.*` |
| `spring.datasource.initialization-mode` | `spring.sql.init.mode` |
| `SpringApplication.run` 返回 `ConfigurableApplicationContext` | 行为不变，但注意 AOT 兼容性 |

---

## 4. 代码规范

### 4.1 包与类命名

```
com.{company}.{service}.{module}.{layer}
例：com.moving.order.service.OrderService
    com.moving.order.domain.entity.Order
    com.moving.order.api.controller.OrderController
    com.moving.order.infra.mapper.OrderMapper
    com.moving.common.result.Result
```

- 类名：PascalCase
- 方法/变量：camelCase
- 常量：`UPPER_SNAKE_CASE`，放在 `XxxConstants` 类
- 禁止：`Util2`、`Helper3`、`Manager2`——有序号的类名是设计问题，先重构再命名

### 4.2 Controller 层

```java
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    // ✅ Controller 只做：参数接收、DTO 转换、权限注解、调用 Service
    @PostMapping
    public Result<OrderVO> create(@Valid @RequestBody CreateOrderReq req) {
        return Result.ok(orderService.create(req));
    }

    // ❌ 禁止在 Controller 写业务判断、直接操作 Mapper
}
```

### 4.3 Service 层

```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)       // 默认只读；写操作方法上加 @Transactional
public class OrderServiceImpl implements OrderService {

    private final OrderMapper orderMapper;

    @Override
    @Transactional                    // 写操作显式标注
    public OrderVO create(CreateOrderReq req) {
        // 业务校验 → 构建 Entity → 持久化 → 触发副作用 → 返回 VO
    }
}
```

**事务注意**：
- `@Transactional` 在同类方法调用时不生效（代理失效），需抽成另一个 Bean 或用 `self` 注入
- 避免在事务内调用外部 HTTP/RPC（锁持有时间不可控）
- 长事务 = 慢查询 + 发消息 + 外部调用，必须拆开

### 4.4 异常处理

```java
// 业务异常：统一通过 BizException 携带错误码
throw new BizException(ErrorCode.ORDER_NOT_FOUND);

// 全局处理器（在 api 模块）
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public Result<Void> handleBiz(BizException e) {
        log.warn("biz error: code={}, msg={}", e.getCode(), e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
            .map(f -> f.getField() + ": " + f.getDefaultMessage())
            .collect(Collectors.joining("; "));
        return Result.fail(ErrorCode.PARAM_ERROR, msg);
    }
}
```

### 4.5 日志

```java
@Slf4j   // Lombok 注解，生成 log 字段
public class OrderService {
    public void process() {
        log.info("processing order: orderId={}", orderId);   // ✅ 参数化
        log.debug("detail: {}", expensiveToString());        // ✅ debug 级别
        // ❌ System.out.println("order: " + order);
        // ❌ log.info("processing order: " + orderId);       // 字符串拼接
    }
}
```

---

## 5. MyBatis-Plus 规范

### 5.1 基础配置（必须）

```yaml
mybatis-plus:
  global-config:
    db-config:
      logic-delete-field: deleted        # 逻辑删除字段
      logic-delete-value: true
      logic-not-delete-value: false
      id-type: assign_id                 # Snowflake ID
  configuration:
    map-underscore-to-camel-case: true
    log-impl: org.apache.ibatis.logging.slf4j.Slf4jImpl
```

### 5.2 Entity 模板

```java
@Data
@TableName("t_order")
public class Order {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String orderNo;

    private Long userId;

    private String status;

    // 时间字段用 OffsetDateTime，不用 LocalDateTime（有时区）
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;

    @TableLogic
    private Boolean deleted;
}
```

### 5.3 LambdaQueryWrapper 用法

```java
// ✅ 推荐：类型安全，重构友好
List<Order> list = orderMapper.selectList(
    new LambdaQueryWrapper<Order>()
        .eq(Order::getUserId, userId)
        .in(Order::getStatus, statuses)
        .eq(Order::getDeleted, false)   // 全局逻辑删除已配置时可省略
        .orderByDesc(Order::getCreatedAt)
);

// ✅ 分页
Page<Order> page = orderMapper.selectPage(
    new Page<>(pageNum, pageSize),
    new LambdaQueryWrapper<Order>().eq(Order::getUserId, userId)
);

// ❌ 禁止：字符串列名（重构时无法感知）
orderMapper.selectList(new QueryWrapper<Order>().eq("user_id", userId));
```

### 5.4 复杂 SQL 放 XML

超过 3 个 JOIN 或含子查询的 SQL 必须放 Mapper XML，不要用字符串拼接：

```xml
<!-- OrderMapper.xml -->
<select id="queryOrderWithDetail" resultType="OrderDetailVO">
    SELECT o.*, s.name AS service_name
    FROM t_order o
    LEFT JOIN t_service s ON s.id = o.service_id
    WHERE o.user_id = #{userId}
      AND o.deleted = false
    ORDER BY o.created_at DESC
</select>
```

---

## 6. Spring Security 6 配置

```java
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/*/auth/**", "/actuator/health").permitAll()
                .requestMatchers("/api/admin/**").hasAnyRole("ADMIN", "OPS", "CS")
                .anyRequest().authenticated()
            )
            .exceptionHandling(e -> e.authenticationEntryPoint(
                new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)
            ))
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
            .build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

JWT Filter 要点：
- 从 `Authorization: Bearer <token>` 提取
- 验证签名 + 过期时间
- 设置 `SecurityContextHolder`，不存 Session
- Token 无效时返回 401，不抛异常（`AuthenticationEntryPoint`）

---

## 7. 统一响应体

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> {
    private int code;
    private String msg;
    private T data;

    public static <T> Result<T> ok(T data) {
        return new Result<>(0, "ok", data);
    }

    public static <T> Result<T> fail(ErrorCode ec) {
        return new Result<>(ec.getCode(), ec.getMessage(), null);
    }

    public static <T> Result<T> fail(int code, String msg) {
        return new Result<>(code, msg, null);
    }

    public static <T> Result<T> fail(ErrorCode ec, String detail) {
        return new Result<>(ec.getCode(), detail, null);
    }
}
```

分页响应体：

```java
@Data
public class PageResult<T> {
    private long total;
    private int page;
    private int size;
    private List<T> list;

    public static <T> PageResult<T> of(Page<T> page) {
        PageResult<T> r = new PageResult<>();
        r.setTotal(page.getTotal());
        r.setPage((int) page.getCurrent());
        r.setSize((int) page.getSize());
        r.setList(page.getRecords());
        return r;
    }
}
```

---

## 8. 配置文件规范

### 8.1 Profile 策略

```
application.yml          ← 公共配置（端口、日志格式、公共 Bean）
application-local.yml    ← 本地开发（不提交，.gitignore）
application-prod.yml     ← 生产（敏感值从环境变量注入）
```

```yaml
# application-prod.yml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  data:
    redis:
      host: ${REDIS_HOST}
      password: ${REDIS_PASSWORD}
```

### 8.2 配置类绑定（不用 `@Value` 散落各处）

```java
@ConfigurationProperties(prefix = "app.jwt")
@Data
public class JwtProperties {
    private String secret;
    private long accessTokenExpireMs = 28800000L;  // 8h
    private long refreshTokenExpireMs = 604800000L; // 7d
}
```

在主类或配置类加 `@EnableConfigurationProperties(JwtProperties.class)`。

---

## 9. 测试规范

### 9.1 单元测试（隔离，快速）

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock  OrderMapper orderMapper;
    @Mock  QuoteMapper quoteMapper;
    @InjectMocks  OrderServiceImpl orderService;

    @Test
    @DisplayName("确认报价时，报价单状态为 REJECTED 应抛 BizException")
    void confirmQuote_rejectedStatus_throwsBizException() {
        Quote quote = new Quote();
        quote.setStatus("REJECTED");
        when(quoteMapper.selectById(1L)).thenReturn(quote);

        assertThatThrownBy(() -> orderService.confirmQuote(1L))
            .isInstanceOf(BizException.class)
            .extracting("code")
            .isEqualTo(ErrorCode.INVALID_STATUS.getCode());
    }
}
```

### 9.2 切片测试（Spring Boot Slice）

比 `@SpringBootTest` 轻量，只加载必要的 Bean，启动快：

```java
// Controller 层切片：只加载 Web 层，Service 需 Mock
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired MockMvc mvc;
    @MockBean OrderService orderService;

    @Test
    void createOrder_validRequest_returns200() throws Exception {
        when(orderService.create(any())).thenReturn(new OrderVO());
        mvc.perform(post("/api/v1/orders")
                .contentType(APPLICATION_JSON)
                .content("""{"quoteId": 1}"""))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.code").value(0));
    }
}

// Mapper / Repository 层切片：只加载持久化层，不启动全量 Context
@MybatisPlusTest  // MyBatis-Plus 专用（需引入 mybatis-plus-boot-starter-test）
// 或用标准 @DataJpaTest（JPA 项目）
@DataJpaTest
@AutoConfigureTestDatabase(replace = NONE)  // 用真实 DB（配合 Testcontainers）
@Testcontainers
class OrderMapperTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine")
            .withInitScript("db/schema.sql");

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", postgres::getJdbcUrl);
        r.add("spring.datasource.username", postgres::getUsername);
        r.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired OrderMapper orderMapper;

    @Test
    void selectByUserId_returnsMatchingOrders() {
        // 直接测 Mapper，不经过 Service 层
    }
}
```

### 9.3 集成测试（Testcontainers）

```java
@SpringBootTest
@Tag("integration")
@Testcontainers
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15-alpine")
            .withInitScript("db/schema.sql");

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
            .withExposedPorts(6379);

    @DynamicPropertySource
    static void configure(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", postgres::getJdbcUrl);
        r.add("spring.datasource.username", postgres::getUsername);
        r.add("spring.datasource.password", postgres::getPassword);
        r.add("spring.data.redis.host", redis::getHost);
        r.add("spring.data.redis.port", () -> redis.getMappedPort(6379));
    }

    // 测试真实 DB + Redis 交互，不 Mock Mapper
}
```

### 9.3 命名规范

```
{被测类/场景}_{条件}_{期望结果}
例：createOrder_withExpiredQuote_throwsBizException
    getOrderList_byUserId_returnsPagedResult
```

---

## 10. 常见陷阱

### 事务代理失效

```java
// ❌ 同类内部调用，事务不生效
@Service
public class OrderService {
    public void outer() {
        this.inner();  // 代理被绕过
    }
    @Transactional
    public void inner() { ... }
}

// ✅ 方案1：抽到另一个 Spring Bean
// ✅ 方案2：注入自身（@Lazy 避免循环依赖）
@Autowired @Lazy private OrderService self;
self.inner();
```

### `@Async` 丢失事务上下文

异步方法在新线程执行，无法继承调用方的事务。异步方法内部需要事务时，必须用自身 `@Transactional`。

### N+1 查询

```java
// ❌ 循环内单条查询
orders.forEach(o -> o.setService(serviceMapper.selectById(o.getServiceId())));

// ✅ 批量查询后 Map 填充
List<Long> serviceIds = orders.stream().map(Order::getServiceId).distinct().toList();
Map<Long, Service> svcMap = serviceMapper.selectBatchIds(serviceIds).stream()
    .collect(Collectors.toMap(Service::getId, s -> s));
orders.forEach(o -> o.setService(svcMap.get(o.getServiceId())));
```

### Jackson 序列化 Long 精度丢失

```java
// Long 超过 JS Number.MAX_SAFE_INTEGER 时前端精度丢失
// ✅ 在全局 ObjectMapper 或字段上加注解
@JsonSerialize(using = ToStringSerializer.class)
private Long id;

// 或全局配置
builder.serializerByType(Long.class, ToStringSerializer.instance);
```

### PostgreSQL TIMESTAMPTZ + OffsetDateTime

```yaml
spring:
  datasource:
    url: jdbc:postgresql://...?options=-c%20TimeZone=UTC
```

```java
// PostgreSQL TIMESTAMPTZ 字段用 OffsetDateTime（含时区信息），不用 LocalDateTime
private OffsetDateTime createdAt;  // ✅
private LocalDateTime createdAt;   // ❌（丢失时区，跨时区部署出 bug）
```

---

## 11. 依赖管理原则

- 新依赖必须在 Maven Central 可查到，使用精确版本号，不用 `LATEST`/`RELEASE`
- 父 pom 为 `spring-boot-starter-parent` 时，Spring 生态依赖（Security、Data、Actuator 等）无需指定版本，由 BOM 管理
- 手动指定版本会覆盖 BOM，**只在已知兼容性问题时才这么做**，并加注释说明原因
- 排除传递依赖时写明原因：

```xml
<exclusion>
    <!-- 使用 logback，排除 log4j2 避免冲突 -->
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-log4j2</artifactId>
</exclusion>
```

---

## 12. Actuator 与健康检查

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
      base-path: /actuator
  endpoint:
    health:
      show-details: when-authorized
```

Docker 健康检查：`curl -sf http://localhost:8080/actuator/health`。

生产环境不暴露 `env`、`beans`、`mappings` 端点（泄露配置）。

---

## 13. 代码审查清单（提交前对照）

- [ ] 新接口是否有 `@Valid` + DTO 字段校验注解？
- [ ] Service 写操作是否有 `@Transactional`？
- [ ] 查询是否会触发 N+1？
- [ ] 异常是否通过 `BizException` 统一处理，而不是裸 `RuntimeException`？
- [ ] 新增环境变量是否同步更新了 `.env.example` 和 `docker-compose.yml`？
- [ ] Long 类型的 ID 字段是否加了 `@JsonSerialize(using = ToStringSerializer.class)`？
- [ ] 日志是否用参数化格式（`log.info("x={}", x)`）？
- [ ] 测试是否覆盖了核心业务逻辑的正常路径和异常路径？
- [ ] 是否意外引入了 `javax.*`（Boot 2 包名）？
