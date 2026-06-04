-- ========================================================
-- 智慧校园图书借阅信息管理系统 V2.0 —— 数据库建表语句
-- MySQL 8.0 + InnoDB + utf8mb4
-- ========================================================

CREATE DATABASE IF NOT EXISTS smart_library_v2
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE smart_library_v2;

-- --------------------------------------------------------
-- 1. 图书分类字典表（中图法）
-- --------------------------------------------------------
CREATE TABLE categories (
    code        VARCHAR(10)     PRIMARY KEY COMMENT '分类编码',
    name        VARCHAR(100)    NOT NULL COMMENT '分类名称',
    level       INT             NOT NULL COMMENT '分类层级',
    parent_code VARCHAR(10)     NULL COMMENT '父级分类编码',
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书分类字典表（中图法）';

-- --------------------------------------------------------
-- 2. 图书主信息表
-- --------------------------------------------------------
CREATE TABLE books (
    isbn             VARCHAR(32)     PRIMARY KEY COMMENT '图书唯一标识（原始哈希ID）',
    barcode          VARCHAR(50)     NOT NULL UNIQUE COMMENT '图书馆内部条码',
    title            VARCHAR(255)    NOT NULL COMMENT '书名',
    authors          VARCHAR(500)    NOT NULL COMMENT '作者列表',
    publisher        VARCHAR(255)    NOT NULL COMMENT '出版社',
    publish_year     INT             NULL COMMENT '出版年份',
    category_code    VARCHAR(10)     NOT NULL COMMENT '分类编码',
    call_no          VARCHAR(100)    NULL COMMENT '索书号',
    language         VARCHAR(20)     DEFAULT '中文' COMMENT '图书语言',
    doc_type         VARCHAR(50)     DEFAULT '普通图书' COMMENT '文献类型',
    total_copies     INT             NOT NULL DEFAULT 1 COMMENT '馆藏总册数',
    available_copies INT             NOT NULL DEFAULT 1 COMMENT '当前可借册数',
    location         VARCHAR(50)     NOT NULL COMMENT '馆藏位置',
    status           VARCHAR(10)     NOT NULL DEFAULT '在库' COMMENT '图书状态：在库/借出/下架/遗失/编目中',
    created_at       DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
    updated_at       DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

    CONSTRAINT fk_book_category FOREIGN KEY (category_code) REFERENCES categories(code),
    -- 真实数据图书ID为32位哈希字符串，取消ISBN长度约束
    CONSTRAINT chk_total_copies_positive CHECK (total_copies >= 0),
    CONSTRAINT chk_available_copies_positive CHECK (available_copies >= 0),
    CONSTRAINT chk_copies_consistency CHECK (total_copies >= available_copies),
    INDEX idx_title (title),
    INDEX idx_category (category_code),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书主信息表';

-- --------------------------------------------------------
-- 3. 图书库存实时表
-- --------------------------------------------------------
CREATE TABLE book_inventory (
    isbn       VARCHAR(32)  PRIMARY KEY COMMENT '图书唯一标识',
    stock      INT          NOT NULL DEFAULT 0 COMMENT '实时库存',
    updated_at DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_inv_isbn FOREIGN KEY (isbn) REFERENCES books(isbn),
    CONSTRAINT chk_stock_positive CHECK (stock >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图书库存实时表';

-- --------------------------------------------------------
-- 4. 用户/读者主表
-- --------------------------------------------------------
CREATE TABLE users (
    id                INT             AUTO_INCREMENT PRIMARY KEY COMMENT '内部主键',
    uid               VARCHAR(20)     NOT NULL UNIQUE COMMENT '学工号',
    real_name         VARCHAR(50)     NOT NULL COMMENT '真实姓名',
    gender            VARCHAR(10)     NULL COMMENT '性别',
    enroll_year       VARCHAR(4)      NULL COMMENT '入学年份',
    department        VARCHAR(100)    NOT NULL COMMENT '院系/部门',
    role              VARCHAR(20)     NOT NULL DEFAULT 'student' COMMENT '角色：student/teacher/libadmin/sysadmin',
    reader_type       VARCHAR(50)     NULL COMMENT '读者类型细分',
    id_type           VARCHAR(20)     NOT NULL DEFAULT '身份证' COMMENT '证件类型',
    id_number_enc     VARCHAR(255)    NOT NULL COMMENT 'AES加密证件号',
    phone_enc         VARCHAR(255)    NOT NULL COMMENT 'AES加密手机号',
    email             VARCHAR(100)    NULL COMMENT '邮箱',
    avatar_path       VARCHAR(255)    NULL COMMENT '头像路径',
    password_hash     VARCHAR(255)    NULL COMMENT 'PBKDF2密码哈希',
    register_time     DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    review_status     VARCHAR(20)     DEFAULT 'pending' COMMENT '审核状态',
    user_status       VARCHAR(20)     DEFAULT 'pending_review' COMMENT '账户状态',
    max_borrow_count  INT             DEFAULT 5 COMMENT '最大可借数量',
    max_borrow_days   INT             DEFAULT 30 COMMENT '最大借阅天数',
    last_login        DATETIME        NULL COMMENT '最后登录时间',
    failed_login_count INT            DEFAULT 0 COMMENT '登录失败次数',
    lock_expires      DATETIME        NULL COMMENT '锁定过期时间',
    access_count      INT             DEFAULT 0 COMMENT '累计入馆次数（预计算）',
    borrow_count      INT             DEFAULT 0 COMMENT '累计借阅册数（预计算）',
    created_at        DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_role (role),
    INDEX idx_department (department),
    INDEX idx_status (user_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户/读者主表';

-- --------------------------------------------------------
-- 5. 用户联系信息扩展表
-- --------------------------------------------------------
CREATE TABLE user_profiles (
    user_id            INT          PRIMARY KEY COMMENT '用户ID',
    wechat_openid      VARCHAR(50)  NULL COMMENT '微信OpenID',
    notify_preference  VARCHAR(50)  DEFAULT 'email,wechat' COMMENT '通知偏好',
    contact_status     VARCHAR(10)  DEFAULT 'active' COMMENT '联系状态',
    updated_at         DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户联系信息扩展表';

-- --------------------------------------------------------
-- 6. 借阅记录主表
-- --------------------------------------------------------
CREATE TABLE borrow_records (
    borrow_id     VARCHAR(32)  PRIMARY KEY COMMENT '借阅流水号',
    user_id       INT          NOT NULL COMMENT '借阅人（users.id）',
    isbn          VARCHAR(32)  NOT NULL COMMENT '图书唯一标识',
    borrow_time   DATETIME     NOT NULL COMMENT '借阅时间',
    due_time      DATETIME     NOT NULL COMMENT '应还时间',
    return_time   DATETIME     NULL COMMENT '实际归还时间',
    operator_id   INT          NULL COMMENT '操作员',
    status        VARCHAR(20)  NOT NULL DEFAULT 'borrowed' COMMENT '借阅状态：borrowed/returned/overdue/renewed/lost',
    overdue_days  INT          DEFAULT 0 COMMENT '逾期天数',
    renew_count   INT          DEFAULT 0 COMMENT '续借次数',
    is_deleted    BOOLEAN      DEFAULT FALSE COMMENT '逻辑删除标记',
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_br_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_br_isbn FOREIGN KEY (isbn) REFERENCES books(isbn),
    INDEX idx_br_user (user_id),
    INDEX idx_br_isbn (isbn),
    INDEX idx_br_status (status),
    INDEX idx_br_borrow_time (borrow_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='借阅记录主表';

-- --------------------------------------------------------
-- 7. 阅览室信息表
-- --------------------------------------------------------
CREATE TABLE reading_rooms (
    room_no   VARCHAR(20)  PRIMARY KEY COMMENT '阅览室编号',
    room_name VARCHAR(100) NOT NULL COMMENT '阅览室名称',
    location  VARCHAR(100) NULL COMMENT '物理位置',
    capacity  INT          NULL COMMENT '座位容量',
    status    VARCHAR(20)  DEFAULT 'open' COMMENT 'open/closed/maintenance'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='阅览室信息表';

-- --------------------------------------------------------
-- 8. 门禁进出日志表
-- --------------------------------------------------------
CREATE TABLE access_logs (
    log_id      BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    user_id     INT          NOT NULL COMMENT '用户ID（users.id）',
    visit_time  DATETIME     NOT NULL COMMENT '进出时间',
    location    VARCHAR(50)  NULL COMMENT '门禁地点',
    access_type VARCHAR(10)  DEFAULT 'in' COMMENT 'in/out',

    CONSTRAINT fk_access_user FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_access_user (user_id),
    INDEX idx_access_time (visit_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='门禁进出日志表';

-- --------------------------------------------------------
-- 9. 座位预约/使用日志表
-- --------------------------------------------------------
CREATE TABLE seat_logs (
    log_id     BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    user_id    INT          NOT NULL COMMENT '用户ID（users.id）',
    room_no    VARCHAR(20)  NOT NULL COMMENT '阅览室编号',
    seat_no    VARCHAR(20)  NOT NULL COMMENT '座位号',
    start_time DATETIME     NOT NULL COMMENT '占座开始时间',
    end_time   DATETIME     NULL COMMENT '离座结束时间',

    CONSTRAINT fk_seat_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_seat_room FOREIGN KEY (room_no) REFERENCES reading_rooms(room_no),
    INDEX idx_seat_user (user_id),
    INDEX idx_seat_room (room_no),
    INDEX idx_seat_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='座位预约/使用日志表';

-- --------------------------------------------------------
-- 10. 权限规则表（RBAC + ABAC）
-- --------------------------------------------------------
CREATE TABLE permission_rules (
    id         INT          AUTO_INCREMENT PRIMARY KEY,
    role       VARCHAR(20)  NOT NULL COMMENT '角色：student/teacher/libadmin/sysadmin',
    resource   VARCHAR(100) NOT NULL COMMENT '资源标识',
    action     VARCHAR(50)  NOT NULL COMMENT '操作',
    condition  VARCHAR(500) NULL COMMENT 'ABAC动态规则表达式',
    created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_perm_role_res_act (role, resource, action),
    INDEX idx_perm_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='权限规则表（RBAC+ABAC）';

-- --------------------------------------------------------
-- 11. 操作审计日志表
-- --------------------------------------------------------
CREATE TABLE audit_logs (
    id          BIGINT       AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL COMMENT '被操作对象用户ID（users.id）',
    action      VARCHAR(50)  NOT NULL COMMENT '操作类型',
    old_value   VARCHAR(255) NULL COMMENT '变更前值',
    new_value   VARCHAR(255) NULL COMMENT '变更后值',
    operator_id INT          NOT NULL COMMENT '执行操作的管理员ID',
    ip_address  VARCHAR(45)  NULL COMMENT '操作者IP',
    user_agent  VARCHAR(255) NULL COMMENT '操作者UA',
    timestamp   DATETIME     DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_time (timestamp),
    INDEX idx_audit_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作审计日志表';

-- --------------------------------------------------------
-- 12. 系统参数配置表
-- --------------------------------------------------------
CREATE TABLE system_config (
    config_key   VARCHAR(50)  PRIMARY KEY COMMENT '参数名',
    config_value VARCHAR(255) NOT NULL COMMENT '参数值',
    description  VARCHAR(255) NULL COMMENT '参数说明',
    updated_at   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统参数配置表';

-- --------------------------------------------------------
-- 13. 通知消息日志表
-- --------------------------------------------------------
CREATE TABLE message_logs (
    log_id        BIGINT       AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    user_id       INT          NOT NULL COMMENT '接收用户ID（users.id）',
    borrow_id     VARCHAR(32)  NULL COMMENT '关联借阅记录',
    channel       VARCHAR(20)  NOT NULL COMMENT '通知渠道：email/wechat/in_app/sms',
    template_code VARCHAR(30)  NOT NULL COMMENT '模板编码',
    content       TEXT         NOT NULL COMMENT '消息正文',
    send_time     DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    status        VARCHAR(10)  DEFAULT 'pending' COMMENT '发送状态：pending/sent/failed',
    error_msg     TEXT         NULL COMMENT '失败原因',
    notify_type   VARCHAR(20)  NOT NULL COMMENT '通知类型',
    notify_level  INT          DEFAULT 1,

    CONSTRAINT fk_msg_borrow FOREIGN KEY (borrow_id) REFERENCES borrow_records(borrow_id),
    INDEX idx_msg_user (user_id),
    INDEX idx_msg_borrow (borrow_id),
    INDEX idx_msg_type_time (notify_type, send_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='通知消息日志表';

-- --------------------------------------------------------
-- 14. 学者库文章数据表（ETL新增）
-- --------------------------------------------------------
CREATE TABLE articles (
    article_id         INT          AUTO_INCREMENT PRIMARY KEY COMMENT '文章自增ID',
    article_type       VARCHAR(50)  NULL COMMENT '文献类型',
    title              VARCHAR(500) NOT NULL COMMENT '文章标题',
    authors            VARCHAR(500) NULL COMMENT '作者',
    author_affiliation VARCHAR(1000) NULL COMMENT '作者单位',
    journal_name       VARCHAR(200) NULL COMMENT '期刊名称',
    issn               VARCHAR(20)  NULL COMMENT '期刊刊号',
    publish_date       VARCHAR(20)  NULL COMMENT '发表时间',
    created_at         DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='学者库文章数据';
